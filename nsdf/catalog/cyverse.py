
import os,sys,requests,time, datetime,urllib3, requests,json,copy, psutil, json, csv, functools
import pprint
from pprint import pprint, pformat

sys.path.append(".")

# ///////////////////////////////////////////////////////////////////////////////////
# https://de.cyverse.org/data/ds/iplant/home/shared/NEON_workshop/data
# https://de.cyverse.org/terrain/docs/index.html
"""
 'id': '15f37e9a-b7ed-11eb-93e7-90e2ba675364',
 'path': '/iplant/home/shared/AG2PI_Workshop_May2021/Utricularia_gibba_PNAS2017.fasta',
 'date-created': 1621350649000,
 'date-modified': 1621367769000,
 'file-size': 101955593,
"""

num_cached_response,num_network_response=0,0
NUM_FILES,TOT_SIZE=0,0
t1=time.time()
__token,__last_token=None,None
io1 = psutil.net_io_counters()
T1=time.time()
CACHE_DIR="/srv/nvme0/nsdf/cyverse-cache"


# ///////////////////////////////////////////////////////////////////////////////////
def cint(value):
	try:
		return int(value)
	except:
		return 0

# /////////////////////////////////////////////////////////////////////////////////// 
def GetToken():
	# renew token every X minutes
	global __token, __last_token
	if __last_token is None or (__last_token-time.time())>20*60:
		username = os.environ["CYVERSE_USERNAME"]
		password = os.environ["CYVERSE_PASSWORD"]
		__token = requests.get("https://de.cyverse.org/terrain/token", auth=(username, password)).json()['access_token']
		print("Got new token")
		__last_token=time.time()
	return __token


# ///////////////////////////////////////////////////////////////////////////////////
def GetResponse(url=None, headers=None, params=None, cache_filename=None):

	global num_cached_response,num_network_response
 
	if os.path.isfile(cache_filename):
		with open(cache_filename,"r") as fin:
			num_cached_response+=1
			return json.loads(fin.read())

	os.makedirs(os.path.dirname(cache_filename),exist_ok=True)
	connection_timeout=10
	response_timeout=60
	response=requests.get(url, verify=True, timeout=(connection_timeout,response_timeout), headers=headers, params=params)
	if response.status_code == 200:
		response=response.json()
		with open(cache_filename,"w") as fout: fout.write(json.dumps(response))
		num_network_response+=1
		return response
	else:
		raise Exception(f'GetNetworkResponse error url={url} response={response}, tried several times')  


# ///////////////////////////////////////////////////////////////////////////////////
def PrintStatistics(current_folder=None, force=False):
	global t1
	if not force and (time.time()-t1)<10.0: return
	t1=time.time()
	io2 = psutil.net_io_counters()
	print(f"current_folder={current_folder} tot_size={TOT_SIZE:,} tot_size-tb={TOT_SIZE/1024**4:.2f} num_files={NUM_FILES:,} num_cached_response={num_cached_response:,} num_network_response={num_network_response:,} num-network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")


# ///////////////////////////////////////////////////////////////////////////////////
def Traverse(csv_writer, folder, rec):
	
	global NUM_FILES, TOT_SIZE
 
	PrintStatistics(folder) 
 
	if "/json/" in folder:
		print(f"Skipping folder=[{folder}] since it is JSON")
		return

	if "magnoliagrandiFLORA/images/specimens" in folder:
		print(f"Skipping folder=[{folder}] since it I don't have access")
		return

	try:
		response = GetResponse(
			url="https://de.cyverse.org/terrain/filesystem/paged-directory", 
			headers={"Authorization": "Bearer " + GetToken(), 'Accept': '`application/json'},
			params={'path': folder, 'entity-type':'any',  'limit':'9999999999999999', 'sort-col':'NAME', 'sort-dir':'ASC'},
			cache_filename=f"{CACHE_DIR}{folder}.json"
 		)
		#print(f"Traverse folder=[{folder}] rec={rec} ok")
	except Exception as ex:
		#print(f"Folder={folder} returned error {ex}")
		return

	# files
	tot_size=0
	files=[file for file in response.get('files',[]) if 'path' in file and 'file-size' in file]
	for file in files:
		# catalog,bucket,name,size,last_modified,etag	
		size=cint(file['file-size'])
		row=["cyverse",os.path.dirname(file['path']),os.path.basename(file['path']),size,file.get('date-modified',''),'']
		tot_size+=size
		csv_writer.writerow(row)
		TOT_SIZE+=size
		NUM_FILES+=1   

	# recursive
	sub_folders=[it for it in response.get('folders',[]) if 'path' in it]
	for sub in sub_folders:
		Traverse(csv_writer, sub['path'],rec+1)

# ///////////////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	with open('/srv/nvme1/nsdf/cyverse.csv', 'w') as fout:
		csv_writer = csv.writer(fout)
		Traverse(csv_writer, "/iplant/home/shared",0)
	PrintStatistics(None,force=True)