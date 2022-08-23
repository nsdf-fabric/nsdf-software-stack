import multiprocessing,queue,time,threading,os,sys
from nsdf.kernel import logger

# ///////////////////////////////////////////////////
class WorkerPool:
    
	class LastResult: pass
	class QuitWorker: pass

	def __init__(self):
		self.lock=multiprocessing.Lock()
		self.processing=0
		self.q=queue.Queue()
		self.results=queue.Queue()
		self.t1=time.time()	
		self.exit=0
		self.workers=[]

	def setMaxConcurrency(self,max_concurrency):
		for n in range(max_concurrency):
			self.startWorker(f"my-thread-{n:02d}",self._workerLoop)
		logger.info(f"Created WorkerPool with {max_concurrency} workers")
   
	def startWorker(self,name,fn):
		worker = threading.Thread(name=name,target=fn)
		self.workers.append(worker)
		worker.start()

	def __iter__(self):
		return self
    
	def __next__(self):
		ret=self.results.get()
		if isinstance(ret,WorkerPool.LastResult):
			self.exit=True
			for worker in range(len(self.workers)):
				self.q.put(WorkerPool.QuitWorker())
			raise StopIteration
		else:
			return ret

	def pushTask(self, task, lock:multiprocessing.Lock=None):
		if not lock:
			with self.lock: 
				return self.pushTask(task,self.lock)
		self.q.put(task)
		self.processing+=1

	def popTask(self,task, lock:multiprocessing.Lock=None):
		if not lock:
			with self.lock: 
				return self.popTask(task,self.lock)     
		self.processing-=1
		if not self.processing:
			self.results.put(WorkerPool.LastResult())

	def _workerLoop(self):
		while True:
			task=self.q.get()
			if isinstance(task,WorkerPool.QuitWorker):  
				return
			task()
			self.popTask(task)