import os,sys, time, io, logging,queue,threading,json,multiprocessing,functools,urllib3,configparser
import botocore
import boto3

logger=logging.getLogger("s3")

# /////////////////////////////////////////////////////////
class S3:

	# constructor
	def __init__(self, url=None, num_connections=10):

		# or you use env variables
		profile=os.environ.get("AWS_PROFILE",None)
		no_verify_ssl=bool(os.environ.get("NO_VERIFY_SSL",False))

		# or you use an url with query params
		if url:
      
			__bucket,__key,qs=S3.parseUrl(url)

			if 'profile' in qs:
				profile=qs['profile'][0]
    
			if 'no-verify-ssl' in qs:
				no_verify_ssl=True
	
			if 'num-connections' in qs:
				num_connections=int(qs['num-connections'][0])
    
		self.session=boto3.session.Session(profile_name=profile)
  
		if no_verify_ssl:
			urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  
		self.num_connections=num_connections
		logger.info(f"Creating S3 url={url} with {num_connections} number of connections")
		botocore_config = botocore.config.Config(max_pool_connections=self.num_connections)
  
		aws_config_filename=os.path.expanduser('~/.aws/config')
		logger.info(f"aws_config_filename={aws_config_filename}") 
		logger.info(f"profile={profile}")
		assert(os.path.isfile(aws_config_filename))
  
		self.client=self.session.client('s3',
			endpoint_url=S3.guessEndPoint(profile,aws_config_filename) if profile else None, 
			config=botocore_config, 
			verify=False if no_verify_ssl else True)

	# parseUrl
	@staticmethod
	def parseUrl(url, is_folder=False):
		from   urllib.parse import urlparse,parse_qs
		parsed=urlparse(url)
		qs=parse_qs(parsed.query, keep_blank_values=True)
		scheme, bucket, key, qs=parsed.scheme, parsed.netloc, parsed.path, qs  
		assert scheme=="s3"
		key=key.lstrip("/")
		if is_folder and key and not key.endswith("/"):
			key=key+"/"
		return bucket,key,qs

	# guessEndPoint
	@staticmethod
	def guessEndPoint(profile,aws_config_filename):
		"""
		[profile cloudbank]
		region = us-west-1
		s3 =
		    endpoint_url = https://s3.us-west-1.amazonaws.com
		"""
		config = configparser.ConfigParser()
		config.read_file(open(aws_config_filename))
		v=[v for k,v in config.items(f'profile {profile}') if k=="s3"]
		if not v: return None
		body="[Default]\n"+v[0]
		config = configparser.ConfigParser()
		config.read_string(body)
		endpoint_url=config.get('Default','endpoint_url')
		return endpoint_url

	# sync
	@staticmethod
	def sync(name, src, dst, no_verify=False):
		from nsdf.kernel import RunCommand
	  
		AWS_ENDPOINT_URL=os.environ["AWS_ENDPOINT_URL"]
		assert AWS_ENDPOINT_URL

		no_verify_opt="--no-verify-ssl" if no_verify else ""

		# is it a glob pattern e.g. /path/to/**/*.png
		if "/**/" in src:
			assert "/**/" in dst
			src_ext=os.path.splitext(src)[1];src=src.split("/**/")[0]
			dst_ext=os.path.splitext(dst)[1];dst=dst.split("/**/")[0]
			assert src_ext==dst_ext
			RunCommand(logger, name, f"aws s3 --endpoint-url={AWS_ENDPOINT_URL} sync --no-progress {no_verify_opt} '{src}' '{dst}' --exclude '*' --include '*{src_ext}'")
		else:
			RunCommand(logger, name, f"aws s3 --endpoint-url={AWS_ENDPOINT_URL} sync --no-progress {no_verify_opt} '{src}' '{dst}'")


	# createTransferManager
	def createTransferManager(self):
		import boto3.s3.transfer as s3transfer
		return s3transfer.create_transfer_manager(self.client, s3transfer.TransferConfig(use_threads=True,max_concurrency=self.num_connections))

	# createUploader
	def createUploader():

		class Uploader:

			# construct
			def __init__(self,s3):
				self.q = queue.Queue()
				self.s3=s3
				self.threads=[]
				for I in range(self.s3.num_connections):
					thread=threading.Thread(target=self.runLoopInBackground, daemon=True)
					self.threads.append(thread)
					thread.start()

			# put
			def put(self,local,remote):
				self.q.put((local,remote))

			# waitAndExit
			def waitAndExit(self):
				for I in range(self.s3.num_connections):
					self.put(None,None)
				self.q.join()

			# runLoopInBackground
			def runLoopInBackground(self):
				while True:
					local,remote = self.q.get()
					if local and remote:
						t1=time.time()
						self.s3.uploadObject(local,remote)
						sec=time.time()-t1
						print(f"Uploaded file {local} in {sec} seconds")
					self.q.task_done()
					if local is None: 
						break
    
		return Uploader(self)

	# createBucket
	def createBucket(self,bucket_name):
		self.client.create_bucket(Bucket=bucket_name)

	# getObject
	def getObject(self,url):
		bucket,key,qs=S3.parseUrl(url)
		t1=time.time()
		body = self.client.get_object(Bucket=bucket, Key=key)['Body'].read()
		logger.debug(f"s3-get_object {key} done in {time.time()-t1} seconds")
		return body

	# putObject
	def putObject(self, url, binary_data):
		bucket,key,qs=S3.parseUrl(url)
		t1=time.time()
		ret=self.client.put_object(Bucket=bucket, Key=key,Body=binary_data)
		assert ret['ResponseMetadata']['HTTPStatusCode'] == 200
		sec=time.time()-t1
		logger.debug(f"s3-put-object {url} done in {sec} seconds")

	# touchObject
	def touchObject(self,url):
		self.putObject(url,"0") # I don't think I can have zero-byte size on S3

	# downloadObject
	def downloadObject(self, url, filename, force=False,nretries=5):
		bucket,key,qs=S3.parseUrl(url)
		
		if not force and os.path.isfile(filename): 
			return 
		t1=time.time()
		os.makedirs( os.path.dirname(filename), exist_ok=True)	
		for retry in range(nretries):
			try:
				self.client.download_file(bucket, key, filename)
				break
			except:
				if retry==(nretries-1):
					logger.error(f"Cannot download_file({bucket}, {key}, {filename})")
					raise
				else:
					time.sleep(0.500)
		
		size_mb=os.path.getsize(filename)//(1024*1024)
		sec=time.time()-t1
		logger.debug(f"s3-download-file {url} {filename}  {size_mb} MiB done in {sec} seconds")

	# uploadObject
	def uploadObject(self, filename, url):
		bucket,key,qs=S3.parseUrl(url)
		size_mb=os.path.getsize(filename)//(1024*1024)
		t1=time.time()
		self.client.upload_file(filename, bucket, key)
		# assert self.existObject(key)
		sec=time.time()-t1
		logger.debug(f"s3-upload-file {filename} {url} {size_mb}MiB done in {sec} seconds")

	# existObject
	def existObject(self, url):
		bucket,key,qs=S3.parseUrl(url)
		try:
			self.client.head_object(Bucket=bucket, Key=key)
			return True
		except:
			return False

	# deleteFolder
	def deleteFolder(self, url):
		bucket,key,qs=S3.parseUrl(url)
		t1=time.time()
		logger.info(f"S3 deleting folder {url}...")
		while True:
			filtered = self.client.list_objects(Bucket=bucket, Prefix=f"{key}/").get('Contents', [])
			if len(filtered)==0: break
			self.client.delete_objects(Bucket=bucket, Delete={'Objects' : [{'Key' : obj['Key'] } for obj in filtered]})
		sec=time.time()-t1
		logger.info(f"S3 delete folder {url} done in {sec} seconds")

	# listObjects
	def listObjects(self,url):
		ret=[]
	  
		# return the list of buckets
		if not url or url=="s3://":
			for it in self.client.list_buckets()['Buckets']:
				bucket=it['Name']
				it['url']=f"s3://{bucket}/"
				ret.append(it)
			return ret 

		# start from a bucket name
		assert url.startswith("s3://")
		if not url.endswith("/"): 
			url+="/"
   
		v=url[5:].split("/",1)
		bucket,key=v[0],v[1] if len(v)>1 else ""
		response = self.client.list_objects(Bucket=bucket, Prefix=key, Delimiter='/')
  
		# folders (end with /) have (Prefix,)
		for it in response.get('CommonPrefixes',[]):
			it['url']=f"s3://{bucket}/{it['Prefix']}"
			ret.append(it)
	  
	  # objects have (ETag,Key,LastModified,Owner.DisplayName,Size,StorageClass,)
		for it in response.get('Contents',[]):
			it['url']=f"s3://{bucket}/{it['Key']}"
			# there is an item which is the folder itself
			if it['url']!=url:
				ret.append(it)

		return ret

	# listObjectsInParallel
	def listObjectsInParallel(self, url, only_dirs=False):
		from nsdf.kernel import WorkerPool
		class ListObjectsInParallel(WorkerPool):

			# constructor
			def __init__(self, s3, url, only_dirs=False):
				super().__init__()
				self.s3=s3
				self.url=url
				self.tot_folders=0
				self.tot_files=0
				self.only_dirs=only_dirs
				self.num_network_requests=0
				self.bucket, self.key, qs=S3.parseUrl(self.url, is_folder=True)
				self.known_folders=set()
				with self.lock:
					self._visitFolder({'Prefix': self.key},self.lock)
				self.setMaxConcurrency(self.s3.num_connections)

			# printStatistics
			def printStatistics(self):
				with self.lock:
					SEC=time.time()-self.t1
					logger.info(f"tot-folders={self.tot_folders} tot-files={self.tot_files} files-per-sec={int(self.tot_files/SEC)} num-network-requests={self.num_network_requests} network-request-per-sec={self.num_network_requests/SEC} ")

			# _visitFolder
			def _visitFolder(self,folder, lock:multiprocessing.Lock):
				prefix=folder['Prefix']
				if prefix in self.known_folders: return
				self.known_folders.add(prefix)
				self.tot_folders+=1
				self.results.put(folder)  
				self.pushTask(functools.partial(self._listObjectsTask,folder,None),lock)

			# _visitFile
			def _visitFile(self, file, lock :multiprocessing.Lock):
				print("_visitFile",file)
				if file['Key'].endswith("/"): 
					assert file['Key'] in self.known_folders # is a folder and I have already added it using CommonPrefix
					return
				self.tot_files+=1
				self.results.put(file)
			  
			# _listObjectsTask
			def _listObjectsTask(self, folder, continuation_token,MaxKeys=1000):
		   
				kwargs=dict(Bucket=self.bucket, Prefix=folder['Prefix'], Delimiter='/', MaxKeys=MaxKeys) # cannot be more than 1000 
				if continuation_token: 
					kwargs['ContinuationToken']=continuation_token
				resp = self.s3.client.list_objects_v2(**kwargs) 
				files  =[] if self.only_dirs else resp.get('Contents',[]) 
				folders=resp.get('CommonPrefixes',[])
				next_continuation_token = resp.get('NextContinuationToken',None)
				logger.debug(f"ListObjectsV2  bucket={self.bucket} folder={folder} num-folders={len(folders)} num-files={len(files)} next_continuation_token={next_continuation_token}")	
				with self.lock as lock:
					self.num_network_requests+=1
					for folder in folders:
						self._visitFolder(folder,self.lock)
					for file in files:
						self._visitFile(file,self.lock)   
					if self.only_dirs and len(folders)<MaxKeys:
						next_continuation_token=None
					if next_continuation_token:
						self.pushTask(functools.partial(self._listObjectsTask,folder,next_continuation_token),lock)
 
		return ListObjectsInParallel(self, url,only_dirs)

	# downloadImage
	#def downloadImage(self, url):
	#	import imageio
	#	ret=imageio.imread(io.BytesIO(self.getObject(url)))
	#	return ret

	# uploadImage
	#def uploadImage(self, img, url):
	#	assert(False) # this function must be tested
	#	bucket,key,qs=S3.parseUrl(url)
	#	buffer = io.BytesIO()
	#	ext = os.path.splitext(key)[-1].strip('.').upper()
	#	img.save(buffer, ext)
		buffer.seek(0)
	#	self.putObject(url, buffer)
