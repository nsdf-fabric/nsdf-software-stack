import sys,shutil,os,time,logging, shlex,time,subprocess,io,threading, queue
from urllib.request import AbstractBasicAuthHandler

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
	def __init__(self,logger=None,aws_profile=None,endpoint_url=None):
		import boto3 
		from nsdf.kernel import logger as nsdf_logger
		self.logger=logger if logger else nsdf_logger

		endpoint_url=os.environ.get("AWS_ENDPOINT_URL",None) if not endpoint_url else endpoint_url
		aws_profile=os.environ.get("AWS_PROFILE",None) if not aws_profile else aws_profile
		region_name=os.environ.get("AWS_DEFAULT_REGION",None)
		aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID",None)
		aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY",None)

		self.session=boto3.session.Session(
			profile_name=aws_profile,
			aws_access_key_id=aws_access_key_id,
			aws_secret_access_key=aws_secret_access_key,
			region_name=region_name)

		self.client=self.session.client('s3',endpoint_url=endpoint_url)

	# __normalize_url
	@staticmethod
	def NormalizeUrl(url):
		assert url.startswith("s3://")
		url=url[len("s3://"):]
		# remove any path
		v=url.split("/",1)
		bucket=v[0]
		key=v[1] if len(v)==2 else ""
		return (bucket,key)

	@staticmethod
	def GetBucket(url):
		return S3.NormalizeUrl(url)[0]

	# createBucket
	def createBucket(self,bucket_name):
		self.self.create_bucket(Bucket=bucket_name)

	# remote -> memory
	def getObject(self,url):
		bucket,key=S3.NormalizeUrl(url)
		t1=time.time()
		body = self.client.get_object(Bucket=bucket, Key=key)['Body'].read()
		self.logger.info(f"s3-get_object {key} done in {time.time()-t1} seconds")
		return body

	# memory -> remote
	def putObject(self, url, binary_data):
		bucket,key=S3.NormalizeUrl(url)
		t1=time.time()
		ret=self.client.put_object(Bucket=bucket, Key=key,Body=binary_data)
		assert ret['ResponseMetadata']['HTTPStatusCode'] == 200
		sec=time.time()-t1
		self.logger.info(f"s3-put-object {url} done in {sec} seconds")

	# remote->local
	def downloadObject(self, url, filename, force=False,nretries=5):
		bucket,key=S3.NormalizeUrl(url)
		if not force and os.path.isfile(filename): return 
		t1=time.time()

		os.makedirs( os.path.dirname(filename), exist_ok=True)	
		for retry in range(nretries):
			try:
				self.client.download_file(bucket, key, filename)
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

	# local -> remote
	def uploadObject(self, filename, url):
		bucket,key=S3.NormalizeUrl(url)
		size_mb=os.path.getsize(filename)//(1024*1024)
		t1=time.time()
		self.client.upload_file(filename, bucket, key)
		# assert self.existObject(key)
		sec=time.time()-t1
		self.logger.info(f"s3-upload-file {filename} {url} {size_mb}MiB done in {sec} seconds")

	# existObject
	def existObject(self, url):
		bucket,key=S3.NormalizeUrl(url)
		try:
			self.client.head_object(Bucket=bucket, Key=key)
			return True
		except:
			return False

	# deleteFolder
	def deleteFolder(self, url):
		bucket,folder=S3.NormalizeUrl(url)
		t1=time.time()
		self.logger.info(f"S3 deleting folder {url}...")
		while True:
			filtered = self.client.list_objects(Bucket=bucket, Prefix=f"{folder}/").get('Contents', [])
			if len(filtered)==0:
				break
			self.client.delete_objects(Bucket=bucket, Delete={'Objects' : [{'Key' : obj['Key'] } for obj in filtered]})
		
		sec=time.time()-t1
		self.logger.info(f"S3 delete folder {url} done in {sec} seconds")

	# only folders, no fonderls
	def listFolders(self,url, recursive=False):
		bucket,folder=S3.NormalizeUrl(url)
		if folder: folder=folder.rstrip("/") + "/" # for non-root make sure it ends wiht /
		paginator = self.client.get_paginator('list_objects_v2')
		pages = paginator.paginate(Bucket=bucket, Prefix=folder, Delimiter='/') 
		for page in pages:
			for obj in page.get('CommonPrefixes',[]):
				sub=os.path.join("s3://",bucket,obj['Prefix'])
				yield sub
				if recursive:
					yield from self.listFolders(sub,True)
			break

	# only objects, no fonderls
	def listObjects(self, url, verbose=True):
		bucket,folder=S3.NormalizeUrl(url)
		t1=time.time()
		if verbose:
			self.logger.info(f"S3 list folder {url}...")
		paginator = self.client.get_paginator('list_objects_v2')
		pages = paginator.paginate(Bucket=bucket, Prefix=folder) 
		N=0
		for page in pages:
			for obj in page.get('Contents',[]):
				N+=1
				yield obj
		if verbose:
			sec=time.time()-t1
			self.logger.info(f"S3 list folder {url} done in {sec}seconds num({N})")

	# downloadImage
	def downloadImage(self, url):
		import imageio
		ret=imageio.imread(io.BytesIO(self.getObject(url)))
		return ret

	# uploadImage ()
	def uploadImage(self, img, url):
		assert(False) # this function must be tested
		bucket,key=S3.NormalizeUrl(url)
		buffer = io.BytesIO()
		ext = os.path.splitext(key)[-1].strip('.').upper()
		img.save(buffer, ext)
		buffer.seek(0)
		self.putObject(url, buffer)


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
		
		self.q = queue.Queue()
		self.s3=S3(logger)

		self.num_connections=num_connections
		self.threads=[]
		for I in range(self.num_connections):
			thread=threading.Thread(target=self.runLoopInBackground, daemon=True)
			self.threads.append(thread)
			thread.start()

	# put
	def put(self,local,remote):
		self.q.put((local,remote))

	# waitAndExit
	def waitAndExit(self):
		for I in range(self.num_connections):
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
		S3(logger).putObject(filename,"0") # I don't think I can have zero-byte size on S3
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
