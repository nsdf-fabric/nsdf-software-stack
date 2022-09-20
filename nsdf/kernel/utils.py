import sys,shutil,os,time,logging, shlex,time,subprocess,io,threading, queue

logger = logging.getLogger("nsdf")

# /////////////////////////////////////////
def GetWorkerId():
	try:
		from requests import get
		ip=get('https://api.ipify.org').text
	except:
		ip="127.0.0.1"

	try:
		from dask.distributed import get_worker
		worker_id =get_worker().id
	except:
		worker_id = 0

	return ip + "-" + str(worker_id)[-3:]

# /////////////////////////////////////////
def SetupLogger(logger, level=logging.INFO, handlers=[]):

	worker_id=GetWorkerId()
	fmt=f"[%(asctime)s][%(levelname)s][%(name)s][%(worker_id)s] %(message)s"

	#datefmt="%Y%m%d %H%M%S"
	datefmt="%H%M%S"

	# see https://discuss.dizzycoding.com/how-do-i-add-custom-field-to-python-log-format-string/
	class AppFilter(logging.Filter):
		def filter(self, record):
			record.worker_id = str(worker_id)
			return True

	logger.addFilter(AppFilter())

	logger.setLevel(level)
	for handler in handlers:
		handler.setLevel(level)
		handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
		logger.addHandler(handler)

	

# /////////////////////////////////////////
def rmdir(dir):
	while os.path.isdir(dir):
		try:
			shutil.rmtree(dir, ignore_errors=False)
		except:
			logger.info(f"Failed to removed directory {dir}, retrying in feww seconds")
			time.sleep(2)
	logger.info(f"Removed directory {dir}")
			
		

# /////////////////////////////////////////
def rmfile(file):
	if os.path.isfile(file):
		os.remove(file)

# /////////////////////////////////////////
def is_jupyter_notebook():
	import __main__ as main
	return not hasattr(main, '__file__')

# /////////////////////////////////////////
def clamp(value,a,b):
	if value<a: value=a
	if value>b: value=b
	return value

# /////////////////////////////////////////
def LoadYaml(filename):
	import yaml
	with open(filename) as file:
		body = yaml.load(file, Loader=yaml.FullLoader)	
	return body

# /////////////////////////////////////////////////////////////////////////
def StringFileSize(size):
	KiB,MiB,GiB,TiB=1024,1024*1024,1024*1024*1024,1024*1024*1024*1024
	if size>TiB: return "{:.1f}TiB".format(size/TiB) 
	if size>GiB: return "{:.1f}GiB".format(size/GiB) 
	if size>MiB: return "{:.1f}MiB".format(size/MiB) 
	if size>KiB: return "{:.1f}KiB".format(size/KiB) 
	return str(size)

# /////////////////////////////////////////////////////////////////////////
def MakeDirForFile(filename):
	try:
		os.makedirs(os.path.dirname(filename),exist_ok=True)
	except:
		pass

# /////////////////////////////////////////////////////////////////////////////
def WriteCSV(filename,rows):
	import csv
	MakeDirForFile(filename)
	with open(filename, 'wt') as f:
		csv.writer(f).writerows(rows)

# ////////////////////////////////////////////////////////////////////////////
def GetPackageDir():
	import nsdf
	return os.path.dirname(nsdf.__file__)

# ////////////////////////////////////////////////////////////////////////
def GetPackageFilename(path):
	import nsdf
	return os.path.join(GetPackageDir(),path)

# ////////////////////////////////////////////////////////////////////////
def RunCommand(logger, name, cmd, verbose=False, nretry=3):

	args=shlex.split(cmd)
	logger.info(f"RunCommand [{name}] {args} running ...")
	t1 = time.time()

	for I in range(nretry):

		result=subprocess.run(args, 
			shell=False, 
			check=False,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT)

		output=result.stdout.decode('utf-8')

		if verbose: 
			logger.info(output)

		if result.returncode==0:
			break

		error_msg=f"RunCommand [{name}] {args} failed with returncode={result.returncode} output:\n{output}"

		if verbose or I==(nretry-1):
			logger.info(error_msg)

		if I==(nretry-1):
			raise Exception(error_msg)

	sec=time.time()-t1
	logger.info(f"RunCommand [{name}] {args} done in {sec} seconds")




# /////////////////////////////////////////////////////////
class S3:

	# constructor
	def __init__(self,logger):
               # os.environ['AWS_ACCESS_KEY_ID'] = '679JYS0BFPLDDA3C975U'
		import boto3 
		self.logger=logger
		self.session=boto3.session.Session()
		self.s3=self.session.client('s3',
			aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"], 
			aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"], 
			region_name=os.environ["AWS_DEFAULT_REGION"],
			endpoint_url=os.environ["AWS_ENDPOINT_URL"])

	# __normalize_url
	@staticmethod
	def NormalizeUrl(url):
		assert url.startswith("s3://")
		url=url[len("s3://"):]
		# remove any path
		bucket,key=url.split("/",1)
		return (bucket,key)

	# createBucket
	def createBucket(self,bucket_name):
		self.self.create_bucket(Bucket=bucket_name)

	# downloadObject
	def downloadObject(self, url, filename, force=False,nretries=5):
		bucket,key=S3.NormalizeUrl(url)
		if not force and os.path.isfile(filename): return 
		t1=time.time()

		os.makedirs( os.path.dirname(filename), exist_ok=True)	
		for retry in range(nretries):
			try:
				self.s3.download_file(bucket, key, filename)
				break
			except:
				if retry==(nretries-1):
					self.logger.error(f"Cannot download_file({bucket}, {key}, {filename})")
					raise
				else:
					time.sleep(0.500)
		
		size_mb=os.path.getsize(filename)//(1024*1024)
		sec=time.time()-t1
		self.logger.info(f"s3-download-file {url} {filename}  {size_mb} MiB done in {sec} seconds")

	# putObject
	def putObject(self, binary_data, url):
		bucket,key=S3.NormalizeUrl(url)
		t1=time.time()
		self.s3.put_object(Bucket=bucket, Key=key,Body=binary_data)
		sec=time.time()-t1
		self.logger.info(f"s3-put-object {url} done in {sec} seconds")

	# uploadObject
	def uploadObject(self, filename, url):
		bucket,key=S3.NormalizeUrl(url)
		size_mb=os.path.getsize(filename)//(1024*1024)
		t1=time.time()
		self.s3.upload_file(filename, bucket, key)		
		# assert self.existObject(key)
		sec=time.time()-t1
		self.logger.info(f"s3-upload-file {filename} {url} {size_mb}MiB done in {sec} seconds")
		## free memory
		import gc
		del filename
		gc.collect()

	# existObject
	def existObject(self, url):
		bucket,key=S3.NormalizeUrl(url)
		try:
			self.s3.head_object(Bucket=bucket, Key=key)
			return True
		except:
			return False

	# deleteFolder
	def deleteFolder(self, url):
		bucket,folder=S3.NormalizeUrl(url)
		t1=time.time()
		self.logger.info(f"S3 deleting folder {url}...")
		while True:
			filtered = self.s3.list_objects(Bucket=bucket, Prefix=f"{folder}/").get('Contents', [])
			if len(filtered)==0:
				break
			self.s3.delete_objects(Bucket=bucket, Delete={'Objects' : [{'Key' : obj['Key'] } for obj in filtered]})
		
		sec=time.time()-t1
		self.logger.info(f"S3 delete folder {url} done in {sec} seconds")

	# listObjects (recursive!)
	def listObjects(self, url, what=None,verbose=True):
		bucket,folder=S3.NormalizeUrl(url)
		t1=time.time()
		if verbose:
			self.logger.info(f"S3 list folder {url}...")
		paginator = self.s3.get_paginator('list_objects_v2')
		pages = paginator.paginate(Bucket=bucket, Prefix=folder) if folder is not None else paginator.paginate(Bucket=bucket)
		ret=[]
		for page in pages:
			for obj in page['Contents'] if 'Contents' in page else []:

				if what=="url":
					ret.append(f"s3://{bucket}/{obj['Key']}")
				else:
					ret.append(obj)
		if verbose:
			sec=time.time()-t1
			self.logger.info(f"S3 list folder {url} done in {sec}seconds num({len(ret)})")
		return ret

	# downloadImage
	def downloadImage(self, url):
		bucket,key=S3.NormalizeUrl(url)
		t1=time.time()
		body = self.s3.get_object(Bucket=bucket, Key=key)['Body'].read()
		import imageio
		ret=imageio.imread(io.BytesIO(body))
		sec=time.time()-t1
		self.logger.info(f"s3-download-image {key} done in {sec} seconds")
		return ret

	# uploadImage ()
	def uploadImage(self, img, url):
		assert(False) # this function must be tested
		bucket,key=S3.NormalizeUrl(url)
		t1=time.time()
		self.logger.info(f"S3 uploading image to {url}...")
		buffer = io.BytesIO()
		ext = os.path.splitext(key)[-1].strip('.').upper()
		img.save(buffer, ext)
		buffer.seek(0)
		ret = self.s3.put_object(Bucket=self.bucket, Key=key, Body=buffer)
		assert ret['ResponseMetadata']['HTTPStatusCode'] == 200
		sec=time.time()-t1
		logger.info(f"s3=upload-image {url} done in {sec} seconds")


# ////////////////////////////////////////////////////////////////////////
def S3Sync(logger, name, src, dst):
	AWS_ENDPOINT_URL=os.environ["AWS_ENDPOINT_URL"]
	assert AWS_ENDPOINT_URL

	# is it a glob pattern e.g. /path/to/**/*.png
	if "/**/" in src:
		assert "/**/" in dst
		src_ext=os.path.splitext(src)[1];src=src.split("/**/")[0]
		dst_ext=os.path.splitext(dst)[1];dst=dst.split("/**/")[0]
		assert src_ext==dst_ext
		RunCommand(logger, name, f"aws s3 --endpoint-url={AWS_ENDPOINT_URL} sync --no-progress '{src}' '{dst}' --exclude '*' --include '*{src_ext}'")
	else:
		RunCommand(logger, name, f"aws s3 --endpoint-url={AWS_ENDPOINT_URL} sync --no-progress '{src}' '{dst}'")


# /////////////////////////////////////////////////////////////////
class S3Uploader:  
	# construct
	def __init__(self,logger, num_connections=1):
		
		self.q = queue.Queue(maxsize=8)
		self.s3=S3(logger)

		self.num_connections=num_connections
		self.threads=[]
		for I in range(self.num_connections):
			thread=threading.Thread(target=self.runLoopInBackground, daemon=True)
			self.threads.append(thread)
			thread.start()

	# put
	def put(self,local,remote):
		if self.q.full():
			time.sleep(1)
		else:
			self.q.put((local,remote))

	# waitAndExit
	def waitAndExit(self):
		for I in range(self.num_connections):
			self.put(None,None)
		self.q.join()

	# runLoopInBackground

	def runLoopInBackground(self):
		while True:
			if self.q.empty():
				time.sleep(1)
			else:
				local,remote = self.q.get()
				if local and remote:
					#t1=time.time()
					self.s3.uploadObject(local,remote)
					#sec=time.time()-t1
					#print(f"Uploaded file {local} in {sec} seconds")
				self.q.task_done()
				if local is None: 
					break



# ////////////////////////////////////////////////////////////////////////
def FileExists(filename):
	if filename.startswith("s3://"):
		return S3(logger).existObject(filename)
	else:
		return os.path.isfile(filename)
	
# ////////////////////////////////////////////////////////////////////////
def TouchFile(filename):
	if FileExists(filename):
		return
	if filename.startswith("s3://"):
		S3(logger).putObject("0",filename) # I don't think I can have zero-byte size on S3
	else:
		open(filename, 'a').close()



# ////////////////////////////////////////////////////////////////////////////////////////
def SafeReplaceFile(filename, new_content):

	assert os.path.isfile(filename)

	temp_filename=filename + ".temp"
	if os.path.isfile(temp_filename): 
		os.remove(temp_filename)
	
	os.rename(filename,temp_filename)

	try:
		with open(filename,"wb") as f:
			f.write(new_content)
	except:
		os.rename(temp_filename,filename) # put back the old file
		raise

	# all ok, remove the old file
	os.remove(temp_filename)


# ////////////////////////////////////////////////////////////////
def LoadVault(filename="~/.nsdf/vault/vault.yaml"):
	from nsdf.kernel import LoadYaml
	return LoadYaml(os.path.expanduser(filename))

# ////////////////////////////////////////////////////////////////
def NormalizeEnv(env):
	ret={}
	for k,v in env.items():
		# possibility to include env from a vault account
		if k=="include-vault":
			accounts=v
			assert isinstance(accounts,tuple) or isinstance(accounts,list)
			from nsdf.kernel import LoadYaml
			vault=LoadVault()
			for account in accounts:
				ret={**ret, **NormalizeEnv(vault[account]["env"])}
		else:
			# safety check, only variable names with all capital letters
			assert k.upper()==k 
			ret[k]=v
	return ret

# ////////////////////////////////////////////////////////////////
def PrintEnv(env):
	for k,v in NormalizeEnv(env).items():
		print(f"export {k}={v}")

# ////////////////////////////////////////////////////////////////
def SetEnv(env):
	for k,v in env.items():
		os.environ[k]=str(v)
