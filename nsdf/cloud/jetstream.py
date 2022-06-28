import os,sys,json, subprocess,socket
from pprint import pprint
import logging



import os,sys,struct,base64,time,socket

from .utils	     import ParallelRun, Check
from .base_ec2   import BaseEc2

# /////////////////////////////////////////////////////
class JetStreamEc2(BaseEc2):

	# constructor
	def __init__(self,config):

		logging.info("JetStreamEc2")
		super().__init__(config)

		self.atmo_base_url=config["atmo-base-url"]
		self.atmo_auth_token=config["atmo-auth-token"]
		self.identity=config["identity"]
		self.size_alias=config["size-alias"]
		self.project=config["project"]
		self.allocation_source_id=config["allocation-source-id"]
		self.image=config["image"]

		logging.info(f"atmo-base-url        = {self.atmo_base_url}")
		logging.info(f"atmo-auth-token      = {self.atmo_auth_token}")
		logging.info(f"identity             = {self.identity}")
		logging.info(f"size-alias           = {self.size_alias}")
		logging.info(f"project              = {self.project}")
		logging.info(f"allocation-source-id = {self.allocation_source_id}")
		logging.info(f"image                = {self.image}")


	# executeCommand
	def executeCommand(self,cmd):
		cmd=["atmo",
			"--atmo-base-url",self.atmo_base_url,
			"--atmo-auth-token",self.atmo_auth_token] + cmd
		cmd=[str(it) for it in cmd]
		#print("CMD:",cmd)
		return subprocess.check_output(cmd).decode('utf-8').strip()

	# createNodes
	def createNodes(self, args):
		uid=args[0]
		logging.info(f"createNodes")

		def runSingle(I):
			cmd=["instance","create",
				"--identity",self.identity,
				"--size-alias",self.size_alias,
				"--project",self.project,
				"--allocation-source-id",self.allocation_source_id,
				"--image",self.image,
				"-f","json",
				f"{uid}-{I}"]
			json.loads(self.executeCommand(cmd))["id"]

		# try to create in parallel to speed up thins
		ParallelRun(runSingle,list(range(self.num)))

		while True:
			nodes=self.getNodes(args)
			#print(nodes)
			public_ips=[]
			for node in nodes:
				public_ip=node["public_ip"]
				if len(public_ip)  and public_ip!="0.0.0.0": 
					public_ips.append(public_ip)

			if len(public_ips)==len(nodes):
				break

			logging.info(f"still waiting for public ips (got {public_ips})...")
			#print(len(public_ips))
			#print(len(nodes))
			time.sleep(5)

		nodes=self.getNodes(args)
		for node in nodes:
			public_ip=node["public_ip"]
			logging.info(f"waiting for ssh port to come up for public_ip...")
			while True:
				if socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex((public_ip,22))==0: 
					break
				logging.info(f"still waiting...")
				time.sleep(5)
			logging.info(f"instance {public_ip} up with port 22 ready")

		return nodes

	# getNodes
	def getNodes(self, args=None):
		uid=args[0] if len(args) else ""

		logging.info(f"getNodes {uid}")
		output=json.loads(self.executeCommand(["instance","list","-f","json"]))

		# filter
		if uid:
			output=[it for it in output if it["name"].startswith(f"{uid}-")] 
		ret=[]
		for it in output:
			public_ip=it['ip_address']
			ret.append({
				'id' : it["uuid"],
				"name" : it["name"],
				'type' : 'node',
				"public_ip": public_ip,
				"ssh-key-name": self.ssh_key_name,
				"ssh-username": self.ssh_username,
				"ssh-key-filename": self.ssh_key_filename,   
				"ssh-command" : f"ssh  -o StrictHostKeyChecking=no -i {self.ssh_key_filename} {self.ssh_username}@{public_ip}" 
			})
		return ret

	# deleteNodes
	def deleteNodes(self, args):
		uid=args[0] if len(args) else ""
		logging.info(f"deleteNodes {uid}")
		for node in self.getNodes(args):
			self.executeCommand(["instance","delete","--force", node["id"]])
			logging.info(f"Destroyed instance {node['id']}")

