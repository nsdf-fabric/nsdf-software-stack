import os,logging, sys
from .utils import GetConfig


# ////////////////////////////////////////////////////////////////////
class BaseEc2:

	# constructor
	def __init__(self, config):

		self.config=config

		self.num			  = int(config["num"]) if "num" in config else 1
		self.num_ips		  = int(config["num-ips"]) if "num-ips" in config else self.num
		self.region		   = config["region"] if "region" in config else ""
		self.ports			= config["ports"] if "ports" in config else "22,443,80,4000" # 4000 if for no-machine 
		self.ssh_key_name	 = config["ssh-key-name"] if "ssh-key-name" in config else ""
		self.ssh_username	 = config["ssh-username"]
		self.ssh_key_filename = config["ssh-key-filename"]

		if isinstance(self.ports,str):
			self.ports =[int(it) for it in self.ports.split(",") if int(it)>0]

		logging.info(f"\t [region={self.region}]")
		logging.info(f"\t [num={self.num}]")
		logging.info(f"\t [num_ips={self.num_ips}]")
		logging.info(f"\t [ports={self.ports}]")
		logging.info(f"\t [ssh_key_name={self.ssh_key_name}]")
		logging.info(f"\t [ssh_username={self.ssh_username}]")
		logging.info(f"\t [ssh_key_filename={self.ssh_key_filename}]")




