
import os,sys,requests,time, datetime,urllib3, requests,json,copy, psutil, json, csv, functools
import pprint
from pprint import pprint, pformat
from nsdf.kernel import WorkerPool

# ///////////////////////////////////////////////////////////////////////////////////
def GetCyverseResponse(url, headers=None, params=None, cache_dir="/srv/nvme0/nsdf/cyverse-cache"):

	# I don't want the token to be considered for caching
	headers_copy=copy.deepcopy(headers)
	headers_copy.pop("Authorization")

	import hashlib
	m5 = hashlib.md5(json.dumps({
	     "url":url, 
	     "headers":headers_copy, 
	     "params": params
     }).encode()).hexdigest()

	cache_filename=os.path.join(cache_dir,f"{m5}.json")
	if os.path.isfile(cache_filename):
		print("Reading",cache_filename)
		with open(cache_filename,"r") as fin:
			return json.loads(fin.read())
	else:
		ret=requests.get(url, verify=True, timeout=(10,60), headers=headers, params=params)
		ret.raise_for_status()
		ret=ret.json()
		os.makedirs(os.path.dirname(cache_filename),exist_ok=True)
		with open(cache_filename,"w") as fout:
			fout.write(json.dumps(ret))
		print("Wrote",cache_filename,"for",url)
		return ret

# ///////////////////////////////////////////////////////////////////////////////////
def Main():

	ROOT_FOLDER='/iplant/home/shared'

	# https://de.cyverse.org/terrain/docs/index.html
	"""
	 'id': '15f37e9a-b7ed-11eb-93e7-90e2ba675364',
	 'path': '/iplant/home/shared/AG2PI_Workshop_May2021/Utricularia_gibba_PNAS2017.fasta',
	 'date-created': 1621350649000,
	 'date-modified': 1621367769000,
	 'file-size': 101955593,
	 ...

	In your terminal export CYVERSE_USERNAME and CYVERSE_PASSWORD
	The first time this script produces a TOKEN, to be exported to the terminal too 
 	"""
	if "CYVERSE_TOKEN" in os.environ:
		CYVERSE_TOKEN=os.environ["CYVERSE_TOKEN"]
	else:
		username = os.environ["CYVERSE_USERNAME"]
		password = os.environ["CYVERSE_PASSWORD"]
		CYVERSE_TOKEN = requests.get("https://de.cyverse.org/terrain/token", auth=(username, password)).json()['access_token']
		print(f"Next time export the token in your shell to reuse it")
		print(f"export CYVERSE_TOKEN={CYVERSE_TOKEN}")
		
	
	io1 = psutil.net_io_counters()
	T1=time.time()
 
	# https://datadryad.org/api/v2/docs/
	# curl -X GET "https://datadryad.org/api/v2/datasets?page=0&per_page=100" -H "accept: application/json"

	def MyTask(pool, folder):
		try:
			folder_body = GetCyverseResponse("https://de.cyverse.org/terrain/filesystem/paged-directory", 
			                 headers={
                     		"Authorization": "Bearer " + CYVERSE_TOKEN, 
                       	'Accept': '`application/json'
                       },
			                 params={
                     		'path':folder, 
                       	'entity-type':'any',  
                        'limit':'9999999999999999'
                       })

			# recursive
			sub_folders=[it for it in folder_body.get('folders',[]) if 'path' in it]
			for sub in sub_folders:
				pool.pushTask(functools.partial(MyTask,pool, sub['path']))
   
			files=[file for file in folder_body.get('files',[]) if 'path' in file and 'file-size' in file]

		except Exception as ex:
			print("ERROR",ex)
			return

		print(f"Processing folder={folder} num-folders={len(sub_folders)} num-files={len(files)}")
		for file in files:
			# catalog,bucket,name,size,last_modified,etag	
			row=["cyverse",os.path.dirname(file['path']),os.path.basename(file['path']),file['file-size'],file.get('date-modified',''),'']
			pool.results.put(row)

	
	sys.path.append(".")
	pool=WorkerPool()
	pool.setMaxConcurrency(4)
	pool.pushTask(functools.partial(MyTask,pool, ROOT_FOLDER))


	with open('/srv/nvme1/nsdf/cyverse.csv', 'w') as fout:
		csv_writer = csv.writer(fout)
		num_files,tot_size=0,0
		for row in pool:
			csv_writer.writerow(row)
			tot_size+=row[3]
			num_files+=1   
			io2 = psutil.net_io_counters()
			print(f"tot_size={tot_size:,} tot_size-tb={tot_size/1024**4:.2f} num_files={num_files:,} num-network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")

  
  
# ///////////////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	Main()