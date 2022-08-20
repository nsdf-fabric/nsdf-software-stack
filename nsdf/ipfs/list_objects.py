
import os,sys,json
import multiprocessing
import time
import threading
import queue
from nsdf.kernel import S3, logger, SetupLogger
from pprint import pprint

if False:
	# SQL LITE EXAMPLE

	DB_FILENAME="db.sqlite3"

	# ____________________________________________________________
	if action=="stats":
		connection = sqlite3.connect(DB_FILENAME)
		cursor = connection.cursor()
		for it in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
			tablename=it[0]
			num,size=cursor.execute(f'select count(*),sum(size) from {tablename}').fetchall()[0]
			print(tablename,num,size)
		connection.commit()
		sys.exit(0)

	# ____________________________________________________________
	if action=="create-table":
		
		tablename=sys.argv[2]
		print(f"create-table {tablename}...")
		t1=time.time()
		connection = sqlite3.connect(DB_FILENAME)
		cursor = connection.cursor()
		cursor.execute(f'CREATE TABLE IF NOT EXISTS {tablename}(key Text, size Integer)')
		cursor.execute(f'CREATE INDEX IF NOT EXISTS {tablename}_index ON {tablename}(key)')
		connection.commit()
	
		# load input from std input (json format
		# exaple {type='file','size':100,'key':'example/key.bin'}
		N,M=0,1*100000
		for line in sys.stdin:
			obj=json.loads(line)
			if obj['type']=='file' and 'size' in obj:
				cursor.execute(f'insert into {tablename} values(?,?)',(obj['key'],int(obj['size'])))
			N+=1
			# do commit once a while
			if N % M==0: 
				sec=time.time()-t1
				print(f"{N:,} {N //sec}")
				connection.commit()
			
		connection.commit()
		print(f"create-table {tablename} done in {time.time()-t1}")
		sys.exit(0)

	# ____________________________________________________________
	if action=="drop-table":
		tablename=sys.argv[2]
		print(f"drop-table {tablename}...")
		connection = sqlite3.connect(DB_FILENAME)
		cursor = connection.cursor()
		cursor.execute(f'DROP INDEX IF EXISTS {tablename}_index')
		cursor.execute(f'DROP TABLE IF EXISTS {tablename}')
		connection.commit()
		sys.exit(0)


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
class ListObjects:

	def __init__(self, s3, s3_url, nworkers):
		self.s3=s3
		self.s3_url=s3_url
		self.lock=multiprocessing.Lock()
		self.q=queue.Queue()
  
		self.t1=time.time()
		self.tot_folders=0
		self.tot_files=0
		self.num_requests=0
		self.last_total=0
  
		self.bucket, up_prefix=S3.NormalizeUrl(self.s3_url)
		self.know_prefixes=set()
		self.out_folders=open("./folders.json","w")
		self.out_files=open("./files.json","w")
  
		self.workers=[]
		for n in range(nworkers):
			self.startWorker(f"thread-list-files-{n:02d}",self.listObjects)
   
		self.addFolder({'Prefix': up_prefix})

	def __del__(self):
		self.out_folders.close()
		self.out_files.close()

	def startWorker(self,name,fn):
		worker = threading.Thread(name=name,target=fn)
		self.workers.append(worker)
		worker.start()
  
	def printStatistics(self):
		t2=time.time()
		if t2-self.t1<10.0: return
		sec=t2-self.t1
		tot=self.tot_folders+ self.tot_files
		objects_per_sec=int((tot-self.last_total)/sec)
		logger.info(f"printStatistics tot-folders={self.tot_folders} tot-files={self.tot_files} num-requests={self.num_requests} objects-per-sec={objects_per_sec}")
		self.t1=time.time()
		self.last_total=tot

  
	def addFolder(self,folder):
		logger.debug(f"addFolder {folder}")
		prefix=folder['Prefix']

		with self.lock:
      
			# already processed?
			if prefix in self.know_prefixes: 
				return

			self.know_prefixes.add(prefix)
      
			self.tot_folders+=1
			if self.out_folders:
				self.out_folders.write(os.path.join("s3://",self.bucket, prefix) + "\n")
    
			# need to do the traversal
			self.q.put(folder)
   
			self.printStatistics()

	def addFile(self, file):
		logger.debug(f"addFile {file}")
		with self.lock:
			self.tot_files+=1
   
			if self.out_files:
				self.out_files.write(json.dumps(file, default=str) + "\n")
    
			self.printStatistics()

	def listObjects(self):
     
		while True:
      
			folder=self.q.get()
			if folder is None:
				return

			prefix=folder['Prefix']

			paginator = s3.client.get_paginator('list_objects_v2')
			pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix, Delimiter='/', MaxKeys=1000) # cann be more than 1000 
			tot_files_in_prefix=0
			for P,page in enumerate(pages):
       
				with self.lock:
					self.num_requests+=1
       
				prefixes=page.get('CommonPrefixes',[])
				files=page.get('Contents',[])
				tot_files_in_prefix+=len(files)
	
				logger.debug(f"listObjects prefix={prefix} page-num={P} num-sub-prefixes={len(prefixes)} num-files-in-page={len(files)} tot-files-in-prefix={tot_files_in_prefix}")
	
				# is it a folder?
				for folder in prefixes:
					self.addFolder(folder)
	
				# is it an file?
				for file in files:
					self.addFile(file)
     


# ///////////////////////////////////////////////////
if True:
	# setup logging

	import logging
	SetupLogger(logger, level=logging.INFO, handlers=[logging.StreamHandler()])

	action=sys.argv[1]
 
	if action=="lines-per-sec":
		N,T1,t1 = 0,time.time(),time.time()
		for line in sys.stdin:
			N+=1
			now=time.time()
			if (now-t1)>2.0:
				t1=now
				sec = now - T1
				print(f"Elapsed time={sec} lines={N:,} lps={N//sec}")
		sys.exit(0)
	

	if action=="list-objects":
		# python3 list_objects.py list-objects
		nworkers=48
		# redis_server = redis.StrictRedis('localhost',6379, charset="utf-8", decode_responses=True)
		s3=S3(aws_profile="wasabi", endpoint_url="https://s3.us-west-1.wasabisys.com") 
		# s3=S3(aws_profile="sealstorage", endpoint_url="https://maritime.sealstorage.io/api/v0/s3") 
		ls=ListObjects(s3, "s3://Pania_2021Q3_in_situ_data",nworkers)
		time.sleep(3600*24*365)
		sys.exit(0)
	#


