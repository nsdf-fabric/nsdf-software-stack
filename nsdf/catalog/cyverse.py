
import os,sys,requests,time, datetime,urllib3, requests,json,copy, psutil, json, csv, functools
import pprint
from pprint import pprint, pformat


sys.path.append(".")
from nsdf.kernel import WorkerPool

num_cached_response=0
num_network_response=0

# /////////////////////////////////////////////////////////////////////////////////// 
def GetNetworkResponse(url, headers={}, params={},connection_timeout=10,response_timeout=60):
	for I in range(3):
		response=requests.get(url, verify=True, timeout=(connection_timeout,response_timeout), headers=headers, params=params)
		if response.status_code == 200:
			return response.json()
		time.sleep(5)
	
	error_msg=f'GetNetworkResponse error url={url} response={response}, tried several times'
	print(error_msg)
	raise Exception(error_msg)


# ///////////////////////////////////////////////////////////////////////////////////
def GetCachedResponse(url, headers=None, params=None):

	global num_cached_response,num_network_response

	CACHE_DIR=os.environ["CACHE_DIR"]
	os.makedirs(CACHE_DIR,exist_ok=True)

	# I don't want the token to be considered for caching
	headers_copy=copy.deepcopy(headers)
	headers_copy.pop("Authorization")

	import hashlib
	m5 = hashlib.md5(json.dumps({
	     "url":url, 
	     "headers":headers_copy, 
	     "params": params
     }).encode()).hexdigest()

	cache_filename=os.path.join(CACHE_DIR,f"{m5}.json")
	if os.path.isfile(cache_filename):
		# print("Reading",cache_filename)
		with open(cache_filename,"r") as fin:
			num_cached_response+=1
			return json.loads(fin.read())
	else:
		num_network_response+=1
		try:
			response=GetNetworkResponse(url, headers=headers, params=params)
		except Exception as ex:
			return ex
		os.makedirs(os.path.dirname(cache_filename),exist_ok=True)
		with open(cache_filename,"w") as fout:
			fout.write(json.dumps(response))
		# print("Wrote",cache_filename,"for",url)
		return response


# ///////////////////////////////////////////////////////////////////////////////////
def cint(value):
	try:
		return int(value)
	except:
		return 0

# ///////////////////////////////////////////////////////////////////////////////////
def Main():

	ROOT_FOLDER='/iplant/home/shared'
	csv_filename='/srv/nvme1/nsdf/cyverse.csv'
 
	os.environ["CACHE_DIR"]="/srv/nvme0/nsdf/cyverse-cache"
	
	# https://de.cyverse.org/terrain/docs/index.html
	"""
	 'id': '15f37e9a-b7ed-11eb-93e7-90e2ba675364',
	 'path': '/iplant/home/shared/AG2PI_Workshop_May2021/Utricularia_gibba_PNAS2017.fasta',
	 'date-created': 1621350649000,
	 'date-modified': 1621367769000,
	 'file-size': 101955593,
	 ...

 	"""

	username = os.environ["CYVERSE_USERNAME"]
	password = os.environ["CYVERSE_PASSWORD"]
	CYVERSE_TOKEN = requests.get("https://de.cyverse.org/terrain/token", auth=(username, password)).json()['access_token']

	io1 = psutil.net_io_counters()
	T1=time.time()
 
	# https://datadryad.org/api/v2/docs/
	# curl -X GET "https://datadryad.org/api/v2/datasets?page=0&per_page=100" -H "accept: application/json"

	t1=time.time()
	def print_stats(force=False):
		nonlocal t1
		if force or (time.time()-t1)>2.0:
			t1=time.time()
			io2 = psutil.net_io_counters()
			print(f"tot_size={tot_size:,} tot_size-tb={tot_size/1024**4:.2f} num_files={num_files:,} num_cached_response={num_cached_response:,} num_network_response={num_network_response:,} num-network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")

	def MyTask(pool, folder):

		folder_body = GetCachedResponse("https://de.cyverse.org/terrain/filesystem/paged-directory", 
		                 headers={
                   		"Authorization": "Bearer " + CYVERSE_TOKEN, 
                     	'Accept': '`application/json'
                     },
		                 params={
                   		'path':folder, 
                     	'entity-type':'any',  
                      'limit':'9999999999999999'
                     })

		if isinstance(folder_body,Exception): 
			print(f"Folder={folder} returned error {folder_body}")
			return

		# recursive
		sub_folders=[it for it in folder_body.get('folders',[]) if 'path' in it]
		for sub in sub_folders:
			pool.pushTask(functools.partial(MyTask,pool, sub['path']))
 
		files=[file for file in folder_body.get('files',[]) if 'path' in file and 'file-size' in file]

		tot_size=0
		for file in files:
			# catalog,bucket,name,size,last_modified,etag	
			size=cint(file['file-size'])
			row=["cyverse",os.path.dirname(file['path']),os.path.basename(file['path']),size,file.get('date-modified',''),'']
			tot_size+=size
			pool.results.put(row)
		
		print(f"Done folder={folder} num-folders={len(sub_folders)} num-files={len(files):,} tot-size={tot_size:,}")
		print_stats()
	
	pool=WorkerPool()
	pool.setMaxConcurrency(4)
	pool.pushTask(functools.partial(MyTask,pool, ROOT_FOLDER))

	with open(csv_filename, 'w') as fout:
		csv_writer = csv.writer(fout)
		num_files,tot_size=0,0
		for row in pool:
			csv_writer.writerow(row)
			tot_size+=row[3]
			num_files+=1   
			print_stats()
		print_stats(force=True)
 
# ///////////////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	Main()