
import os,sys,requests,time, datetime,urllib3, requests,json,copy, psutil, json, csv, functools
import pprint
from pprint import pprint, pformat

sys.path.append(".")

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
def GetCachedResponse(cache_filename, url, headers=None, params=None):

	global num_cached_response,num_network_response
 
	if os.path.isfile(cache_filename):
		# print("Reading",cache_filename)
		with open(cache_filename,"r") as fin:
			num_cached_response+=1
			return json.loads(fin.read())
	else:
		os.makedirs(os.path.dirname(cache_filename),exist_ok=True)
		try:
			response=GetNetworkResponse(url, headers=headers, params=params)
		except Exception as ex:
			print(ex)
			return ex
		
		with open(cache_filename,"w") as fout:
			fout.write(json.dumps(response))
		print("Wrote",cache_filename,"for",url)
		num_network_response+=1
		return response


# ///////////////////////////////////////////////////////////////////////////////////
def cint(value):
	try:
		return int(value)
	except:
		return 0

# ///////////////////////////////////////////////////////////////////////////////////
def Main():

	# https://de.cyverse.org/data/ds/iplant/home/shared/NEON_workshop/data
	ROOT_FOLDER='/iplant/home/shared'
	csv_filename='/srv/nvme1/nsdf/cyverse.csv'
	
	# https://de.cyverse.org/terrain/docs/index.html
	"""
	 'id': '15f37e9a-b7ed-11eb-93e7-90e2ba675364',
	 'path': '/iplant/home/shared/AG2PI_Workshop_May2021/Utricularia_gibba_PNAS2017.fasta',
	 'date-created': 1621350649000,
	 'date-modified': 1621367769000,
	 'file-size': 101955593,
	 ...

 	"""
	CYVERSE_TOKEN=None
	last_token=None
 
	io1 = psutil.net_io_counters()
	T1=time.time()
 
	NUM_FILES,TOT_SIZE=0,0

	t1=time.time()
	def print_stats(current_folder=None, force=False):
		nonlocal t1
		if force or (time.time()-t1)>2.0:
			t1=time.time()
			io2 = psutil.net_io_counters()
			print(f"current_folder={current_folder} tot_size={TOT_SIZE:,} tot_size-tb={TOT_SIZE/1024**4:.2f} num_files={NUM_FILES:,} num_cached_response={num_cached_response:,} num_network_response={num_network_response:,} num-network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")

	def Traverse(csv_writer, folder,rec):
		
		nonlocal NUM_FILES,TOT_SIZE
		CACHE_DIR="/srv/nvme0/nsdf/cyverse-cache"

		# renew token every X minutes
		nonlocal CYVERSE_TOKEN, last_token
		if last_token is None or (last_token-time.time())>20*60:
			username = os.environ["CYVERSE_USERNAME"]
			password = os.environ["CYVERSE_PASSWORD"]
			CYVERSE_TOKEN = requests.get("https://de.cyverse.org/terrain/token", auth=(username, password)).json()['access_token']
			print("Got CYVERSE_TOKEN",CYVERSE_TOKEN)
			last_token=time.time()
  
		folder_body = GetCachedResponse(
    								f"{CACHE_DIR}{folder}.json",
            				"https://de.cyverse.org/terrain/filesystem/paged-directory", 
		                 headers={
                   		"Authorization": "Bearer " + CYVERSE_TOKEN, 
                     	'Accept': '`application/json'
                     },
		                 params={
                   		'path': folder, 
                     	'entity-type':'any',  
                      'limit':'9999999999999999',
                      'sort-col':'NAME',
                      'sort-dir':'ASC'
                     })

		if isinstance(folder_body,Exception): 
			print(f"Folder={folder} returned error {folder_body}")
			return
 
		# files
		tot_size=0
		files=[file for file in folder_body.get('files',[]) if 'path' in file and 'file-size' in file]
		for file in files:
			# catalog,bucket,name,size,last_modified,etag	
			size=cint(file['file-size'])
			row=["cyverse",os.path.dirname(file['path']),os.path.basename(file['path']),size,file.get('date-modified',''),'']
			tot_size+=size
			csv_writer.writerow(row)
			TOT_SIZE+=size
			NUM_FILES+=1   
			print_stats(folder)
 
		# recursive
		sub_folders=[it for it in folder_body.get('folders',[]) if 'path' in it]
		for sub in sub_folders:
			Traverse(csv_writer, sub['path'],rec+1)
			print_stats(folder)  

		# print(f"Done folder={folder} num-folders={len(sub_folders)} num-files={len(files):,} tot-size={tot_size:,}"
	
	with open(csv_filename, 'w') as fout:
		csv_writer = csv.writer(fout)
		Traverse(csv_writer, ROOT_FOLDER,0)
		print_stats(None,force=True)
 
# ///////////////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	Main()