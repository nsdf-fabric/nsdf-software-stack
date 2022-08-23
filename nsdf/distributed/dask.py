import os,sys, dask, time
import pprint,threading,select

from nsdf.kernel import logger,MakeDirForFile
from dask.distributed import Client, LocalCluster,  LocalCluster, Nanny, Worker, SpecCluster,Security

import prefect
from   prefect import Flow, Parameter, Task, task,unmapped
from   prefect.executors import DaskExecutor,LocalDaskExecutor
from   prefect.executors import DaskExecutor

import distributed
from dask.distributed import WorkerPlugin

import distributed.deploy.ssh

from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager

import pickle, logging, logging.handlers,socketserver, struct

# /////////////////////////////////////////////////////////
class LogRecordStreamHandler(socketserver.StreamRequestHandler):

	# handle
	def handle(self):
		while True:
			chunk = self.connection.recv(4)
			if len(chunk) < 4: break
			slen = struct.unpack('>L', chunk)[0]
			chunk = self.connection.recv(slen)
			while len(chunk) < slen:
				chunk = chunk + self.connection.recv(slen - len(chunk))
			obj = self.unPickle(chunk)
			record = logging.makeLogRecord(obj)
			self.handleLogRecord(record)

	# unPickle
	def unPickle(self, data):
		return pickle.loads(data)

	# handleLogRecord
	def handleLogRecord(self, record):
		logger.handle(record)

# /////////////////////////////////////////////////////////
class SendLogsToCentralHost(logging.handlers.SocketHandler):
	
	def __init__(self, central_host, central_port):
		super().__init__(central_host,central_port)
		from nsdf.kernel import 
		self.worker_id=GetWorkerId()

	def emit(self, record):
		record.msg= f"[{self.worker_id}] " + record.msg
		super().emit(record)


# /////////////////////////////////////////////////////////
class NSDFWorkerPlugin(distributed.diagnostics.plugin.WorkerPlugin):

	# constructor
	def __init__(self, get_cuda_device, central_host,central_port):
		self.get_cuda_device=get_cuda_device
		self.central_host=central_host
		self.central_port=central_port

	# setup
	def setup(self, worker):
		
		import os, sys

		# NOTE I am sure I will have problem here, worker.id it's here a string like `Worker-d90f26cf-4753-45fb-8aa8-4f1ef70a2a8a`
		#      instead I am probably expecting something like `tcp://10.140.81.223:33207``
		#      but I think it should be solvable adding some print(worker) here
		if self.get_cuda_device:
			os.environ['CUDA_VISIBLE_DEVICES']=self.get_cuda_device[worker.id]

		# make sure I can find the NSDF package
		nsdf_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir,os.pardir))
		if not nsdf_dir in sys.path:
			sys.path.append(nsdf_dir)

		import logging
		logger = logging.getLogger("nsdf")

		# set  file logger for the NSDF
		from nsdf.kernel import logger, SetupLogger

		from dask.distributed import get_worker
		worker_local_dir=get_worker().local_directory

		# add a file logger for the DASK worker
		if True:
			dask_logger=logging.getLogger("distributed.worker")
			os.makedirs(worker_local_dir,exist_ok=True)
			SetupLogger(dask_logger, level=logging.INFO, handlers=[ 
				logging.FileHandler(f"{worker_local_dir}/dask.worker.log")])

		if True:
			os.makedirs(worker_local_dir,exist_ok=True)
			SetupLogger(logger, level=logging.INFO, handlers=[
				logging.StreamHandler(),
				logging.FileHandler(f"{worker_local_dir}/nsdf.log"),
				SendLogsToCentralHost(self.central_host,self.central_port)])

		logger.info(f"NSDFWorkerPlugin setup done {worker.id}")

	# transition
	def transition(self, key, start, finish, *args, **kwargs):
		pass


# /////////////////////////////////////////////////////////
class ReceiveLogsFromWorkers(socketserver.ThreadingTCPServer):

	allow_reuse_address = True

	# constructor
	def __init__(self, host='127.0.0.1', port=0):
		super().__init__((host, port), LogRecordStreamHandler)
		self.port = port
		self.abort = 0
		self.timeout = 1

	# start
	def start(self):
		
		self.listener=threading.Thread(target=self.runLoopInBackground)
		self.listener.start()

	# stop
	def stop(self):
		self.abort=True
		self.listener.join()

	# runLoopInBackground
	def runLoopInBackground(self):
		abort = 0
		while True:
			if self.abort: 
				break
			rd, wr, ex = select.select([self.socket.fileno()],[], [], self.timeout)
			if rd: 
				self.handle_request()

# ////////////////////////////////////////////////////
class NSDFDaskCluster:

	#  constructor
	def __init__(self,args):

		# containing ansible hosts
		ansible_inventory=args["inventory"]

		# group to use
		ansible_group=args.get("group","all")

		# this is the number of process per host
		num_process_per_host=int(args.get("num-process-per-host",1))

		# keep it to 1, prefer to use multi-processing vs nthreads for GIL and CUDA problem
		nthreads=int(args.get("nthreads",1))
		assert nthreads==1	

		# where to store temporary files
		worker_local_dir=str(args.get("worker-local-dir","/tmp/nsdf/dask-workers"))

		# if cuda is needed
		need_cuda=bool(args.get("need-cuda",False))

		
		
			
		# central logging
		from requests import get
		central_host = get('https://api.ipify.org').text
		central_port=13489			


		# extract information from ansible file
		inventory = InventoryManager(
			loader=DataLoader(),
			sources=[ansible_inventory])

		hosts=inventory.get_groups_dict()[ansible_group]

		ansible_vars=inventory.groups[ansible_group].get_vars()
		ansible_connection=ansible_vars.get("ansible_connection","local")
		username=ansible_vars.get("ansible_user","")
		private_key_file=ansible_vars.get("ansible_ssh_private_key_file","")
		python_interpreter=ansible_vars.get("ansible_python_interpreter","")

		# environment variables for ssh worker
		if True:
			python_environment_variables=args.get("env",{})
			# KEY1=value2 KEY2=value2 python3 whatever args here
			s_value=" ".join([f"{k}={v}" for k,v in python_environment_variables.items()])
			python_interpreter=f"{s_value} {python_interpreter}"

		logger.info("RunDaskCluster:")
		logger.info(f"  hosts                   {hosts}")
		logger.info(f"  ansible_connection      {ansible_connection}")
		logger.info(f"  username                {username}")
		logger.info(f"  private_key_file        {private_key_file}")
		logger.info(f"  num_process-per-host    {num_process_per_host}")
		logger.info(f"  nthreads                {nthreads}")
		logger.info(f"  worker-local-dir        {worker_local_dir}")
		logger.info(f"  need_cuda               {need_cuda}")
		logger.info(f"  python_interpreter      <...>")

		# https://github.com/dask/distributed/blob/main/distributed/deploy/local.py
		# https://github.com/dask/distributed/blob/main/distributed/deploy/ssh.py

		assert ansible_connection=="ssh" or ansible_connection=="local"

		dashboard_address=":8787"
		
		if ansible_connection=="ssh":

			# first host is scheduler
			scheduler={
				"cls": distributed.deploy.ssh.Scheduler,
				"dashboard": True,
				"dashboard_address" : dashboard_address,
				"options": {
					"address": hosts[0],
					# see https://docs.dask.org/en/stable/deploying-cli.html
					"kwargs": {
						#"host" : hosts[0],
						#"port":8786,
					},
					"remote_python": python_interpreter,
					"connect_options": {
						"known_hosts": None,
						"username": username,
						"client_keys": private_key_file
					}
				}
			}		

			# note: each host has num_process_per_host
			workers={}
			for i, worker_address in enumerate(hosts):

				# https://github.com/dask/distributed/blob/main/distributed/deploy/ssh.py
				# https://github.com/dask/distributed/blob/main/distributed/nanny.py
				# https://github.com/rapidsai/dask-cuda/blob/dea27d52c10bd135c24c26626369ebe691d2c217/dask_cuda/cuda_worker.py

				# there will be one ssh.Worker for each host, and each one will lunch num_process_per_host 
				# internally ssh.Worker is doing:
				#   python -m distributed.cli.dask_spec <scheduler> --spec "{i: {"cls": self.worker_class,  "opts": {kwargs}  } 
				
				workers[i]={
					"cls": distributed.deploy.ssh.Worker,
					"options": {
							"address": worker_address,
							"remote_python": python_interpreter,
							"connect_options": {
								"known_hosts": None,
								"username": username,
								"client_keys": private_key_file
							},
							"worker_class": "distributed.Nanny",

							# see https://docs.dask.org/en/stable/deploying-cli.html
							"kwargs": {
								"n_workers": num_process_per_host,
								"nthreads": 1,
								"local_directory": worker_local_dir,
								"memory_limit": 0, # to disable memory control by dask (not sure it it's the best solution but I am having too many shutdown from DASK for automatic memory limits)
							},
					}
				}

		else:

			scheduler={
				"cls" : distributed.scheduler.Scheduler,
				"dashboard": True,
				"dashboard_address" : dashboard_address,
				"options" : {
					"host": "127.0.0.1",
					"port": 0,
					"protocol": "tcp://"
			}}

			workers={}
			for i in range(num_process_per_host):
				workers[i]={
					"cls": dask.distributed.Nanny, 
					"options": {
						"host": "127.0.0.1",
						"nthreads": 1,
						"dashboard_address": dashboard_address,
						"dashboard": False,
						"protocol": "tcp://",
						"local_directory": worker_local_dir,
						"memory_limit": 0, # to disable memory control by dask (not sure it it's the best solution but I am having too many shutdown from DASK for automatic memory limits)
					}
				}

		#logger.info(f"scheduler specs: \n{pprint.pformat(scheduler)}")
		#logger.info(f"workers   #({len(workers)}) specs: \n{pprint.pformat(workers)}")
		self.cluster=SpecCluster(scheduler=scheduler,  workers=workers)
		self.address=self.cluster.scheduler_info["address"]
		logger.info(f"Cluster started address({self.address})")

		with self.connect() as client:
			
			# wait workers to be ready
			if True:
				tot_workers=len(hosts) * num_process_per_host
				assert nthreads==1
				while True:
					
					"""
					Example:
					{
						'tcp://10.140.81.223:33207': {
							'type': 'Worker', 
							'id': 'tcp://10.140.81.223:33207', 
							'host': '10.140.81.223', 
							'resources': {}, 
							'local_directory': '/tmp/nsdf/dask-workers/dask-worker-space/worker-c0aoyn1m', 
							'name': 'tcp://10.140.81.223:33207', 
							'nthreads': 1, 
							'memory_limit': 0, 
							'last_seen': 1656057923.7009735, 
							'services': {'dashboard': 33507}, 
							'status': 'running', 
							'nanny': 'tcp://10.140.81.223:46075'
					}, 
					"""

					workers=client.scheduler_info()["workers"]
					if len(workers)== tot_workers: break
					logger.info(f"Waiting for all workers ready={len(workers)} tot={tot_workers}...")
					time.sleep(1)


			self.receive_logs_from_workers=ReceiveLogsFromWorkers(host="", port=central_port)
			self.receive_logs_from_workers.start()

			if need_cuda:
				get_cuda_device={}
				workers_per_ip={}
				for worker_id in workers:
					# example: tcp://10.140.81.223:33207
					protocol, ip_port=worker_id.split("://")
					ip, port=ip_port.split(":")
					if not ip in workers_per_ip: workers_per_ip[ip]=[]
					get_cuda_device[worker_id]=len(workers_per_ip[ip])
					workers_per_ip[ip].append(worker_id)
			else:
				get_cuda_device=None

			plugin=NSDFWorkerPlugin(get_cuda_device if need_cuda else None, central_host, central_port)
			client.register_worker_plugin(plugin) 

	# execute
	def execute(self,flow, tasks=[]):

		executor = DaskExecutor(address=self.address,debug=False) 
		state=flow.run(executor=executor)

		logger.info("Flow State:")
		logger.info(state)
		for task in tasks:
			logger.info(f"{task}  status={state.result[task]} result={task.result}")
		logger.info("")

		return state
		
	# connect
	def connect(self):
		return Client(self.address)

	# close
	def close(self):
		
		logger.info("Shutting down cluster 1/2...")
		self.receive_logs_from_workers.stop()

		logger.info("Shutting down cluster 2/2...")
		self.cluster.close()

		logger.info(f"Cluster close done ")	




