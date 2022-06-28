import os,sys
from pprint import pprint
import logging

import os,sys,struct,base64,time,socket

# see https://pypi.org/project/vultr/
# pip install vultr
from vultr import Vultr

from .utils	  import ParallelRun, Check
from .base_ec2   import BaseEc2

# /////////////////////////////////////////////////////
class VultrEc2(BaseEc2):

	# constructor
	def __init__(self,config):

		logging.info("VultrEc2")
		super().__init__(config)

		self.api_key=config["api-key"]
		self.conn=Vultr(self.api_key)

		self.VPSPLANID=self.config["VPSPLANID"]  
		self.OSID=self.config["OSID"]
		self.DCID=[int(it["DCID"]) for it in self.getRegions() if it["name"]==self.region][0] 
		
		# find the key_id from the name
		self.SSHKEYID=""
		for k,v in self.conn.sshkey.list().items():
			if v['name']==self.ssh_key_name:
				self.SSHKEYID=v["SSHKEYID"]
				break
		Check(self.SSHKEYID,"Cannot find the ssh key_name, did you install it?")

		logging.info(f"\t [VPSPLANID={self.VPSPLANID}]")
		logging.info(f"\t [OSID={self.OSID}]")	
		logging.info(f"\t [DCID={self.DCID}]")		   
		logging.info(f"\t [SSHKEYID={self.SSHKEYID}]") 

	# getPlans
	def getPlans(self,args=None):
		return list(self.conn.plans.list().values())

	# getOs
	def getOs(self,args=None):
		return list(self.conn.os.list().values())

	# getRegions
	def getRegions(self,args=None):
		return list(self.conn.regions.list().values())

	# createNodes
	def createNodes(self, args):
		
		uid=args[0]
		logging.info(f"createNodes")

		# remember: we are using the API v1 (not v2) because the python package is old
		ids=[0]*self.num
		def runSingle(I):
			single=self.conn.server.create(
				self.DCID, 
				self.VPSPLANID, 
				self.OSID,
				{
					'label': uid, 
					'SSHKEYID' : self.SSHKEYID 
				})
			ids[I]=single["SUBID"]

		# try to creatre in parallel to speed up thins
		ParallelRun(runSingle,list(range(self.num)))

		for id in ids:
			logging.info(f"waiting for public ip...")
			public_ip=None
			while True:
				public_ip=self.conn.server.list(subid=id)["main_ip"]
				if public_ip!="0.0.0.0": break
				logging.info(f"still waiting...")
				time.sleep(5)
			logging.info(f"got public_ip {public_ip}")

			logging.info(f"[3]waiting for ssh port to come up...")
			while True:
				if socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex((public_ip,22))==0: break
				logging.info(f"still waiting...")
				time.sleep(5)
			logging.info(f"instance ready")

		return self.getNodes(args)


	# getNodes
	def getNodes(self, args):
		uid=args[0]
		logging.info(f"getNodes {uid}")
		servers=self.conn.server.list()
		ret=[]
		for k,v in servers.items():
			if v["location"]==self.region and v["label"]==uid:
				public_ip=v['main_ip']
				ret.append({
					'id' : k,
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
		uid=args[0]
		logging.info(f"deleteNodes {uid}")
		for instance in self.getNodes(args):
			self.conn.server.destroy(instance["id"])  
			instance_id=instance["id"]
			logging.info(f"Destroyed instance {instance_id}")

