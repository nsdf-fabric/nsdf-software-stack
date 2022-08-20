
import os,sys, boto3, time, imageio, io

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
