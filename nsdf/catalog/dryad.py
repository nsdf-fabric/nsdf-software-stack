import os,sys,requests,time, datetime,urllib3,psutil
import pprint
from pprint import pprint, pformat
import json, csv

from ratelimit import limits, RateLimitException, sleep_and_retry


# ///////////////////////////////////////////////////////////////////////////////////
@sleep_and_retry
@limits(calls=30, period=60) 
def GetJSONResponse(url, headers=None, params=None):
	ret=requests.get(url, verify=True, timeout=(10,60), headers=headers,params=params)
	if ret.status_code!=200:
		raise Exception(f"Cannot get response for url={url} got {ret.status_code} {ret.reason}")
	return ret.json()

# ///////////////////////////////////////////////////////////////////////////////////
def GetDryadResponse(url, headers=None, params=None, cache_dir="/srv/nvme0/nsdf/dryad-cache"):

	import hashlib
	m5 = hashlib.md5(json.dumps({
	     "url":url, 
	     "headers":headers, 
	     "params": params
     }).encode()).hexdigest()
	  
	cache_filename=os.path.join(cache_dir,f"{m5}.json")
	if os.path.isfile(cache_filename):
		print("Reading",cache_filename)
		with open(cache_filename,"r") as fin:
			return json.loads(fin.read())
	else:
		print("Writing",cache_filename)
		ret=GetJSONResponse(url,headers=headers, params=params)
		os.makedirs(os.path.dirname(cache_filename),exist_ok=True)
		with open(cache_filename,"w") as fout:
			fout.write(json.dumps(ret))
		return ret
    


# ///////////////////////////////////////////////////////////////////////////////////
def Main():

	io1 = psutil.net_io_counters()
	T1=time.time()
	
	HOST="https://datadryad.org"
	
	DATASETS=[]
	dataset_next=f"/api/v2/datasets?page=0&per_page=100"
	while dataset_next:
		print(dataset_next)
		try:
			datasets_body=GetDryadResponse(f"{HOST}{dataset_next}",headers={"accept": "application/json"})
			dataset_links=datasets_body['_links']
			datasets=datasets_body['_embedded']['stash:datasets']
			DATASETS.extend(datasets)
		except:
			raise

		# next dataset link
		try:
			dataset_next=dataset_links['next']['href']
		except:
		    dataset_next=None


	io2 = psutil.net_io_counters()
	print(f" total-datasets={len(DATASETS)} num-network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")

	# https://datadryad.org/api/v2/docs/
	# curl -X GET "https://datadryad.org/api/v2/datasets?page=0&per_page=100" -H "accept: application/json"
	with open('/srv/nvme1/nsdf/dryad.csv', 'w') as fout:
		csv_writer = csv.writer(fout)
  
		num_files,tot_size=0,0
		
		for D,dataset in enumerate(DATASETS):
			try:
				dataset_id=dataset['id']
				version=dataset['_links']['stash:version']['href']
			except:
				continue
			
			print("DATASET",D,len(DATASETS))

			# get all files
			file_next=f"{version}/files?page=0&per_page=100"
			while file_next:
				try:
					files_body=GetDryadResponse(f"{HOST}{file_next}",headers={"accept": "application/json"})
					file_links=files_body.get('_links',None)
					files=files_body['_embedded']['stash:files']
				except:
					continue

				for file in files:
					# catalog,bucket,name,size,last_modified,etag
					row=["dryad",dataset_id,file.get('path',''),file.get('size',0),"",file.get('digest','')]
					tot_size+=row[3]
					num_files+=1
					csv_writer.writerow(row)
     
				try:
					file_next=files_body['_links']['next']['href']
				except:
					file_next=None
  
			io2 = psutil.net_io_counters()
			print(f" tot_size={tot_size:,} num_files={num_files:,} num-network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")
			

# ///////////////////////////////////////////////////////////////
if __name__=="__main__":
	Main()