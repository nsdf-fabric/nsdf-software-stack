
import os,sys,json,multiprocessing,time,threading,queue
from pprint import pprint

from nsdf.kernel import logger,WorkerPool
from nsdf.s3 import S3ParseUrl,S3
import functools 

if False:

	# REDIS LITE EXAMPLE

	# python3 -m pip install redis
	# sudo apt install redis
	# redis-server --daemonize yes
	# ps aux | grep redis-server
	import redis

	# ////////////////////////////////////////////////////////////////////////////
	class Queue(object):
		
		"""
		someone publishes, only one get the message
		"""
		
		def __init__(self, redis_server, stream_name):
			self.redis_server = redis_server
			self.stream_name=stream_name

		def write(self, data):
			self.redis_server.rpush(self.stream_name, json.dumps(data, default=str))

		def read(self):
			data=json.loads(self.redis_server.blpop(self.stream_name)[1])
			return data

	# ////////////////////////////////////////////////////////////////////////////
	class PubSub(object):
		
		"""
		someone publishes, all subscribers get the message
		"""    
		
		def __init__(self, redis_server, stream_name):
			self.redis_server = redis_server
			self.stream_name=stream_name
			self.sub=None

		def write(self,  data):
			self.redis_server.publish(self.stream_name, json.dumps(data, default=str))

		def read(self):
			if self.sub is None:
				self.sub=self.redis_server.pubsub()
				self.sub.subscribe(self.stream_name)
	
			for msg in self.sub.listen():
				if msg is not None and isinstance(msg,dict) and msg['type']=='message':
					data=json.loads(msg['data'])
					return data

	if action=="test-publisher":
		"""
  		python3 list_objects.py test-publisher queue| pubsub
		"""
		import redis
		redis_server = redis.StrictRedis('localhost',6379, charset="utf-8", decode_responses=True)
		p=Queue(redis_server,"my-stream") if sys.argv[2]=="queue" else PubSub(redis_server,"pubsub")
  
		for I in range(1024**4):
			msg={"key":I}
			p.write(msg)
			# logger.info("published message",msg)
		sys.exit(0)
  
	if action=="test-subscriber":
		"""
  		python3 list_objects.py test-subscriber queue| pubsub
    	"""     
		redis_server = redis.StrictRedis('localhost',6379, charset="utf-8", decode_responses=True)
		p=Queue(redis_server,"my-stream") if sys.argv[2]=="queue" else PubSub(redis_server,"pubsub")
		cont=0
		t1=time.time()
		while True:
			# logger.info(p.read())
			cont+=1
			t2=time.time()
			if (cont % 1000000) ==0:
				sec=time.time()-t1
				print(f"{int(cont/sec):,}")

		sys.exit(0)
    
# ///////////////////////////////////////////////////
def ListObjectsV2(client, bucket, folder, continuation_token=None):

	kwargs=dict(Bucket=bucket, Prefix=folder['Prefix'], Delimiter='/', MaxKeys=1000) # cann be more than 1000 
	if continuation_token: 
		kwargs['ContinuationToken']=continuation_token

	resp = client.list_objects_v2(**kwargs) 
	files, folders=resp.get('Contents',[]), resp.get('CommonPrefixes',[])
	next_continuation_token = resp.get('NextContinuationToken',None)
	logger.debug(f"listObjects  bucket={bucket} folder={folder} num-folders={len(folders)} num-files={len(files)} next_continuation_token={next_continuation_token}")	
	return (files,folders,next_continuation_token)

   

# ///////////////////////////////////////////////////
class ListObjects(WorkerPool):

	def __init__(self, url):
		super().__init__()
		self.s3=S3(url) 
		self.url=url
		self.tot_folders=0
		self.tot_files=0
		self.num_network_requests=0
		self.bucket, self.key, qs=S3ParseUrl(self.url, is_folder=True)
		self.known_folders=set()
		with self.lock:
			self._visitFolder({'Prefix': self.key},self.lock)
		self.setMaxConcurrency(self.s3.num_connections)

	def printStatistics(self):
		with self.lock:
			SEC=time.time()-self.t1
			TOT=self.tot_folders+self.tot_files
			logger.info(f"tot-folders={self.tot_folders} tot-files={self.tot_files} num-network-requests={self.num_network_requests} objects-per-sec={int(TOT/SEC)}")

	def _visitFolder(self,folder, lock:multiprocessing.Lock):
		prefix=folder['Prefix']
		if prefix in self.known_folders: return
		self.known_folders.add(prefix)
		self.tot_folders+=1
		self.results.put(folder)  
		self._pushTask(functools.partial(self._listObjectsTask,folder,None),lock)
   
	def _visitFile(self, file, lock :multiprocessing.Lock):
		if file['Key'].endswith("/"): 
			assert file['Key'] in self.known_folders # is a folder and I have already added it using CommonPrefix
			return
		self.tot_files+=1
		self.results.put(file)
  
	def _listObjectsTask(self, folder, continuation_token):
		files, folders, next_continuation_token=ListObjectsV2(self.s3.client,self.bucket, folder,continuation_token)
  
		with self.lock:
			self.num_network_requests+=1

			for folder in folders:
				self._visitFolder(folder,self.lock)
    
			for file in files:
				self._visitFile(file,self.lock)   

			if next_continuation_token:
				self._pushTask(functools.partial(self._listObjectsTask,folder,next_continuation_token),self.lock)


