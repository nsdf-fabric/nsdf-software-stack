
import os,sys, boto3, time, imageio, io
import botocore
from nsdf.kernel import ParseUrl
from nsdf.kernel import logger 
import boto3.s3.transfer as s3transfer

# /////////////////////////////////////////////////////////
def S3ParseUrl(url, is_folder=False):
	scheme, bucket, key, qs=ParseUrl(url)
	assert scheme=="s3"
	key=key.lstrip("/")
	if is_folder and key and not key.endswith("/"):
		key=key+"/"
	return bucket,key,qs

# /////////////////////////////////////////////////////////
def S3GuessEndPoint(profile,aws_config_filename='~/.aws/config'):
	"""
	[profile cloudbank]
	region = us-west-1
	s3 =
	    endpoint_url = https://s3.us-west-1.amazonaws.com
	"""
	import configparser
	config = configparser.ConfigParser()
	config.read_file(open(os.path.expanduser(aws_config_filename)))
	v=[v for k,v in config.items(f'profile {profile}') if k=="s3"]
	if not v: return None
	body="[Default]\n"+v[0]
	config = configparser.ConfigParser()
	config.read_string(body)
	endpoint_url=config.get('Default','endpoint_url')
	return endpoint_url

# /////////////////////////////////////////////////////////
class S3:

	# constructor
	def __init__(self, url=None, num_connections=10):
     
		profile=os.environ.get("AWS_PROFILE",None)
		no_verify_ssl=bool(os.environ.get("NO_VERIFY_SSL",False))

		if url:
      
			__bucket,__key,qs=S3ParseUrl(url)

			if 'profile' in qs:
				profile=qs['profile'][0]
    
			if 'no-verify-ssl' in qs:
				no_verify_ssl=True
	
			if 'num-connections' in qs:
				num_connections=int(qs['num-connections'][0])
    
		self.session=boto3.session.Session(profile_name=profile)
  
		if no_verify_ssl:
			import urllib3
			urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  
		self.num_connections=num_connections
		logger.info(f"Creating S3 url={url} with {num_connections} number of connections")
		botocore_config = botocore.config.Config(max_pool_connections=self.num_connections)
  
		self.client=self.session.client(
			's3',
			endpoint_url=S3GuessEndPoint(profile) if profile else None, 
			config=botocore_config, 
			verify=False if no_verify_ssl else True
			)

	def createTransferManager(self):
		return s3transfer.create_transfer_manager(self.client, s3transfer.TransferConfig(use_threads=True,max_concurrency=self.num_connections))

	# createBucket
	def createBucket(self,bucket_name):
		self.client.create_bucket(Bucket=bucket_name)

	def getObject(self,url):
		bucket,key,qs=S3ParseUrl(url)
		t1=time.time()
		body = self.client.get_object(Bucket=bucket, Key=key)['Body'].read()
		logger.debug(f"s3-get_object {key} done in {time.time()-t1} seconds")
		return body

	def putObject(self, url, binary_data):
		bucket,key,qs=S3ParseUrl(url)
		t1=time.time()
		ret=self.client.put_object(Bucket=bucket, Key=key,Body=binary_data)
		assert ret['ResponseMetadata']['HTTPStatusCode'] == 200
		sec=time.time()-t1
		logger.debug(f"s3-put-object {url} done in {sec} seconds")

	def downloadObject(self, url, filename, force=False,nretries=5):
		bucket,key,qs=S3ParseUrl(url)
		if not force and os.path.isfile(filename): return 
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

	def uploadObject(self, filename, url):
		bucket,key,qs=S3ParseUrl(url)
		size_mb=os.path.getsize(filename)//(1024*1024)
		t1=time.time()
		self.client.upload_file(filename, bucket, key)
		# assert self.existObject(key)
		sec=time.time()-t1
		logger.debug(f"s3-upload-file {filename} {url} {size_mb}MiB done in {sec} seconds")

	def existObject(self, url):
		bucket,key,qs=S3ParseUrl(url)
		try:
			self.client.head_object(Bucket=bucket, Key=key)
			return True
		except:
			return False

	def deleteFolder(self, url):
		bucket,key,qs=S3ParseUrl(url)
		t1=time.time()
		logger.info(f"S3 deleting folder {url}...")
		while True:
			filtered = self.client.list_objects(Bucket=bucket, Prefix=f"{key}/").get('Contents', [])
			if len(filtered)==0: break
			self.client.delete_objects(Bucket=bucket, Delete={'Objects' : [{'Key' : obj['Key'] } for obj in filtered]})
		sec=time.time()-t1
		logger.info(f"S3 delete folder {url} done in {sec} seconds")


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
  
		from pprint import pprint
		pprint(response)

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

	def downloadImage(self, url):
		ret=imageio.imread(io.BytesIO(self.getObject(url)))
		return ret

	def uploadImage(self, img, url):
		assert(False) # this function must be tested
		bucket,key,qs=S3ParseUrl(url)
		buffer = io.BytesIO()
		ext = os.path.splitext(key)[-1].strip('.').upper()
		img.save(buffer, ext)
		buffer.seek(0)
		self.putObject(url, buffer)
