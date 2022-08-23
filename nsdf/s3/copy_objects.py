import multiprocessing,time,os,sys,copy, functools,uuid, threading
from nsdf.kernel import WorkerPool

import clickhouse_driver 

from nsdf.s3 import S3,S3ParseUrl
from nsdf.kernel import HumanSize,logger

# S3 CopyObject API will work only under the same echosystem (e.g. not wasaby->aws or aws->wasaby)
# think about endpoint-url , we have no way to pass it to the copy API
# https://docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html
# https://stackoverflow.com/questions/70168961/copy-object-from-minio-bucket-to-s3-bucket
# The copy() command tells Amazon S3 to copy an object within the Amazon S3 ecosystem. 
# It can be used to copy objects within the same bucket, or between buckets, even if those buckets are in different Regions.
# Bottom line: You'll need to download the files from one system and upload them to the other.
# dst.client.copy(CopySource={'Bucket': 'Pania_2021Q3_in_situ_data','Key': 'visus.idx'},Bucket='utah', Key='visus3.idx', SourceClient=src.client)


if False:
	"""
	OLD CODE WITH TRANSFER MANAGER
	finished=multiprocessing.Condition()
	Stm=Ss3.createTransferManager()
	Dtm=Ds3.createTransferManager()

	class MyTransferManagerSubscriber(BaseSubscriber):
		def __init__(self,callback):
			self.callback=callback
		def on_queued(self, future, **kwargs):
			pass
		def on_progress(self, future, bytes_transferred, **kwargs):
			pass
		def on_done(self, **kwargs):
			self.callback()

	def CopyObject(row, local, stage):
		Skey, last_modified,etag,size,storage_class = row
		Dkey=Dprefix+Skey

		if local is None:
			local=os.path.join(tmpdirname,str(uuid.uuid4()))
		 
		if stage=="download":
			future=Stm.download(Sbucket, Skey, local, subscribers=[MyTransferManagerSubscriber(functools.partial(CopyObject, row, local, "upload"))])
		elif next=="upload":
			future=Dtm.upload(local, Dbucket, Dkey, subscribers=[MyTransferManagerSubscriber(functools.partial(CopyObject, row, local, "finish"))])
		else:
			Ddb.execute('INSERT INTO sealstorage VALUES',[[Dkey,last_modified,etag,size,storage_class]])
			stats.increment([("bytes_done",size),("files_done",1)])
			try:
				CopyObject(next(objects), None, "download")
			except StopIteration:
				with finished: finished.notify()

	num_connections=min(Ss3.num_connections,Ds3.num_connections)
	for I in range(num_connections):
		try:
			CopyObject(next(objects), None, "download")
		except StopIteration:
			break
	with finished: finished.wait()
	Stm.shutdown(cancel=False)
	Dtm.shutdown(cancel=False)
	"""



# ////////////////////////////////////////////////////
class Stats:

	def __init__(self,lock=None):
		self.lock=lock if lock else multiprocessing.Lock()
		self.values={
			'time' : time.time(),
			"bytes_done" : 0,
			"tot_bytes" : 0,
			"files_done" : 0,		
			"tot_files" : 0
		}	
		self.last_values=copy.copy(self.values)

	def increment(self,values):
		with self.lock:
			for k,v in values:
				self.values[k]+=v
			self._print(self.lock)
   
	def _print(self,lock,force=False):
		self.values['time']=time.time()
		sec=self.values['time']-self.last_values['time']
		if sec==0 or (sec<1.0 and not force): return
		mb_sec=int((self.values['bytes_done']-self.last_values['bytes_done']/sec) / 1024**2)
		logger.info(f"bytes={HumanSize(self.values['bytes_done'])}/{HumanSize(self.values['tot_bytes'])} files={self.values['files_done']:,}/{self.values['tot_files']:,} mb/sec={mb_sec}")
		self.last_values=copy.copy(self.values)

	def print(self):
		with self.lock:
			self._print(self.lock, force=True)

# ////////////////////////////////////////////////////
class CopyObjects(WorkerPool):

	class EndPoint: pass

	def __init__(self, src, dst, tmp_dir):
		
		super().__init__()
		self.tmp_dir=tmp_dir
  
		self.src=CopyObjects.EndPoint()
		self.src.db=clickhouse_driver.Client(host="localhost", port=str(9000))
		self.src.s3=S3(url=src)
		self.src.bucket,self.src.prefix,_=S3ParseUrl(src,is_folder=True)

		self.dst=CopyObjects.EndPoint()
		self.dst.db=clickhouse_driver.Client(host="localhost", port=str(9000))
		self.dst.s3=S3(url=dst)
		self.dst.bucket,self.dst.prefix,_=S3ParseUrl(dst,is_folder=True)

		self.setMaxConcurrency(max(self.src.s3.num_connections,self.dst.s3.num_connections))
  
		if True:
			worker = threading.Thread(name="push-all-tasks",target=self._pushAllTasks)
			self.workers.append(worker)
			worker.start()

	def _pushAllTasks(self):
		tot_files,tot_bytes=self.src.db.execute("""
			SELECT count(*),sum(src.Size) FROM pania AS src 
			LEFT JOIN (select Key from sealstorage) dst 
			ON dst.Key=CONCAT('buckets/Pania_2021Q3_in_situ_data/',src.Key) WHERE dst.Key=''"""
			)[0]
  
		self.stats=Stats()
		self.stats.increment([("tot_bytes",tot_bytes),("tot_files",tot_files)])
		self.stats.print()

		rows=self.src.db.execute_iter(f"""
			SELECT src.* FROM pania AS src LEFT JOIN (select Key from sealstorage) dst ON dst.Key=CONCAT('{self.dst.prefix}',src.Key) WHERE dst.Key='' 
			""",
			settings={'max_block_size': 10000})

		for row in rows:
			with self.lock:
				if self.exit:
					return
				self._pushTask(functools.partial(self._copyObjectTask,row),self.lock)


	def _copyObjectTask(self, src_row):
		Skey, last_modified,etag,size,storage_class = src_row
		Dkey=self.dst.prefix+Skey

		src_url=f"s3://{self.src.bucket}/{Skey}"
		dst_url=f"s3://{self.dst.bucket}/{Dkey}"
		local=os.path.join(self.tmp_dir,str(uuid.uuid4()))
		dst_row=[Dkey,last_modified,etag,size,storage_class]
  
		ex=None
		try:
			self.src.s3.downloadObject(src_url, local)
			self.dst.s3.uploadObject(local, dst_url)
			self.stats.increment([("bytes_done",size),("files_done",1)])
		except Exception as ex_:
			ex=ex_
			logger.error(f"Problems happened copying {Skey} exception={ex}")
		finally:
			if os.path.isfile(local):
				os.remove(local)

		from threading import current_thread
		# logger.info(f"f'Done {current_thread().name}' {Skey}")
		with self.lock:
			self.results.put((src_row,dst_row,str(ex)))
