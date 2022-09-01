
import os,sys,requests,time, datetime,urllib3, requests,json,copy, psutil, json, csv, functools
from this import d
import pprint
from pprint import pprint, pformat

sys.path.append(".")
from nsdf.kernel import WorkerPool

num_network_request=0
num_cached_request=0
num_products=0

# ///////////////////////////////////////////////////////////////////////////////////
from ratelimit import limits, RateLimitException, sleep_and_retry
@limits(calls=60, period=60) 
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
def GetCachedResponse(url, headers={}, params={}):
	global num_cached_request,num_network_request

	CACHE_DIR=os.environ["CACHE_DIR"]
	os.makedirs(CACHE_DIR,exist_ok=True)

	# I don't want the token to be considered for caching
	headers_copy=copy.deepcopy(headers)
	if "Authorization" in headers_copy:
		headers_copy.pop("Authorization")

	import hashlib
	m5 = hashlib.md5(json.dumps({
	     "url":url, 
	     "headers":headers_copy, 
	     "params": params
     }).encode()).hexdigest()

	cache_filename=os.path.join(CACHE_DIR,f"{m5}.json")
	if os.path.isfile(cache_filename):
		num_cached_request+=1
		# print("Reading",cache_filename)
		with open(cache_filename,"r") as fin:
			return json.loads(fin.read())
	else:
		# print("GetNetworkResponse",url, cache_filename, os.path.isfile(cache_filename))
		try:
			ret=GetNetworkResponse(url, headers,params)
		except Exception as ex:
			return None # failed, do not care...
		num_network_request+=1
		os.makedirs(os.path.dirname(cache_filename),exist_ok=True)
		with open(cache_filename,"w") as fout:
			fout.write(json.dumps(ret))
		# print("Wrote",cache_filename,"for",url)
		return ret

# ///////////////////////////////////////////////////////////////////////////////////
def cint(value):
	try:
		return int(value)
	except:
		return 0

# ///////////////////////////////////////////////////////////////////////////////////
def Main():

	# https://data.neonscience.org/data-api/endpoints
 
	os.environ["CACHE_DIR"]="/srv/nvme0/nsdf/neon-cache"
	cvs_filename='/srv/nvme0/nsdf/neon.csv'

	# Example of visus viewer
	# https://data.neonscience.org/data-products/DP3.30026.001
 
	os.makedirs(os.path.dirname(cvs_filename),exist_ok=True)
	with open(cvs_filename, 'w') as fout:

		csv_writer = csv.writer(fout)

		io1 = psutil.net_io_counters()
		T1=time.time()
		t1=time.time()

		num_files,tot_size=0,0
		known_products=set()
		known_releases=set()

		# ///////////////////////////////////////////////////
		def print_stats(force=False):
			nonlocal t1
			if force or time.time()-t1 > 2.0:
				t1=time.time()
				io2 = psutil.net_io_counters()
				print(f"tot_size={tot_size:,} tot_size-tb={tot_size/1024**4:.2f} num_files={num_files:,} num_products={num_products} num-network-request={num_network_request} num-cached-request={num_cached_request} num-network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")
		# ///////////////////////////////////////////////////
		def append_row(row):
			nonlocal num_files,tot_size, csv_writer,t1
			num_files+=1
			tot_size+=row[3]
			csv_writer.writerow(row)

		# ///////////////////////////////////////////////////
		def visitFile(productCode,siteCode, file):
			if not productCode or not siteCode or not file: return
			name=file["name"] #"NEON.D16.ABBY.DP1.00001.001.000.020.002.2DWSD_2min.2019-08.basic.20220115T171830Z.csv",
			size=cint(file["size"]) #2346693,
			md5=str(file.get("md5",file.get("crc32",file.get("crc32c"))))
			url=file["url"] 
			append_row(["neon",f"file-{productCode}-{siteCode}",name,size,'',md5])
			print_stats()
			return size

		# ///////////////////////////////////////////////////
		def visitRelease(release):
			if not release: return
			nonlocal known_releases
    
			uuid=release["uuid"]
			if uuid in known_releases: return
			known_releases.add(uuid)
   
			# print("visitRelease",uuid)
   
			# artifacts 
			for artifact in release.get("artifacts",[]):
				append_row(["neon",f"release-{uuid}",artifact["name"],cint(artifact["size"]),"",artifact.get("md5",'')])    

			# dataProducts (==new products)
			for data_product in release.get("dataProducts",[]):
				productCode=data_product["productCode"]
				response=GetCachedResponse(f"https://data.neonscience.org/api/v0/products/{productCode}")
				if response:
					visitProduct(response.get("data",None))
			
			print_stats()
	
		# ///////////////////////////////////////////////////
		def visitSpec(productCode, spec):
			if not productCode or not spec: return
			specId=spec["specId"] # "8365",
			specNumber=spec["specNumber"] # "NEON.DOC.000780vD"
			specType=spec["specType"] # "application/pdf",
			specSize=cint(spec.get("specSize",0)) # 715529,
			specDescription=spec["specDescription"] # "NEON Algorithm Theoretical Basis Document (ATBD) – 2D Wind Speed and Direction",
			specUrl=spec["specUrl"] # "https://data.neonscience.org/api/v0/documents/NEON.DOC.000780vD"
			# catalog,bucket,name,size,last_modified,etag
			append_row(["neon",f"spec-{productCode}-{specId}",specNumber,specSize,"",""])
			print_stats()
			return specSize
    
    # ///////////////////////////////////////////////////
		def visitProduct(product):
			if not product: return
			global num_products
			nonlocal known_products
			productCode=product["productCode"] # DP1.00001.001
			if productCode in known_products: return
			known_products.add(productCode)
   
			num_files=0
			tot_size=0
			num_products+=1

			# spec
			specs=product.get("specs",[])
			for spec in specs if specs else []:
				tot_size+=visitSpec(productCode, spec)
				num_files+=1
   
			# releases
			releases=product.get("releases",[])
			for release in releases:
				response=GetCachedResponse(release["url"])
				if response:
					visitRelease(response.get("data",None))

			# site codes (contains files too, called 'data')
			site_codes=product.get("siteCodes",[])
			for sitecode in site_codes if site_codes else []:
				siteCode=sitecode["siteCode"]
				for url in sitecode["availableDataUrls"]:
					response=GetCachedResponse(url)
					if response and "data" in response:
							for file in response["data"].get("files",[]):
								tot_size+=visitFile(productCode, siteCode, file)
								num_files+=1

			print(f"visitProduct productCode={productCode} num-files={num_files:,} tot_size={tot_size:,}")
			print_stats()

		# curl -X 'GET' 'https://data.neonscience.org/api/v0/products' -H 'accept: application/json'
		# curl -X 'GET' 'https://data.neonscience.org/api/v0/releases -H 'accept: application/json'
		response=GetCachedResponse("https://data.neonscience.org/api/v0/products")
		if response:
			for product in response.get("data",[]):
				visitProduct(product)
		print_stats(force=True)

# ///////////////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	Main()