import queue,threading,time,os,sys
from .s3 import S3


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
