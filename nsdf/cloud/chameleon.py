# see https://github.com/ChameleonCloud/python-chi

import os,sys,struct,base64,time,socket,argparse,copy
from pprint import pprint
import logging
import traceback
from .base_ec2 import BaseEc2

# pip3 install python-chi
import chi
from chi.lease		import lease_duration,add_node_reservation, add_fip_reservation,create_lease, get_node_reservation, delete_lease, get_reserved_floating_ips
from chi.server	   import Server, wait_for_tcp, associate_floating_ip, create_server, get_server_id, list_servers, delete_server
from chi.network	  import get_free_floating_ip 

from .utils import Check

# /////////////////////////////////////////////////////////////////////////
class ChameleonEC2(BaseEc2):

	# constructor
	def __init__(self, config):

		logging.info(f"ChameleonEC2")  
		super().__init__(config)

		# IMPORTANT if you use environment variable you should call this to force a reload
		# chi.reset()
		env=config["env"]

		for k,v in env.items():
			Check(k.startswith("OS_"))
			k=k.lower()[3:] # remove OS_
			v=str(v).strip()
			chi.set(k,v)

		chi.use_site(env["OS_REGION_NAME"])														  
		chi.set("project_name", env["OS_PROJECT_NAME"])
		session = chi.session()

		self.node_type	=	 self.config["node-type"]
		self.image_name   =	 self.config["image-name"]
		self.network_name =	 self.config["network-name"]
		self.lease_days   =	 int(self.config["lease-days"])

		logging.info(f"\t [node_type={self.node_type}]")
		logging.info(f"\t [image_name={self.image_name}]")
		logging.info(f"\t [network_name={self.network_name}]")
		logging.info(f"\t [lease_days={self.lease_days}]")

	# createLease
	def createLease(self,uid, num, num_ips, node_type, lease_days):

		logging.info(f"Creating lease")
		while True:
			
			ex=None
			try:

				# making as long as possible..
				# see https://chameleoncloud.readthedocs.io/en/latest/technical/reservations.html#:~:text=To%20ensure%20fairness%20to%20all,request%20if%20resources%20are%20available.
				start_date, end_date = lease_duration(days=lease_days) 

				reservations=[]
				add_node_reservation(reservations, count=num, node_type=node_type)
				add_fip_reservation(reservations,  count=num_ips)

				lease = create_lease(uid, reservations, start_date=start_date,end_date=end_date)
			except Exception as __ex:
				ex=traceback.format_exc()

			if ex:
				logging.info(f"Lease creation failed {ex} trying again...")
				time.sleep(5) 
				continue
				
			logging.info(f"lease created {uid}")
			logging.info(f"now waiting lease...")
			chi.lease.wait_for_active(uid)
			logging.info(f"lease ready {uid}")
			return lease

		raise Exception("cannot create the lease")	

	# createNodes
	def createNodes(self, args):
		
		uid=args[0]
		logging.info(f"createinstances {uid}")

		Check(self.num>0 and self.num<100) # safety check

		if True:
			self.createLease(uid, self.num, self.num_ips,self.node_type, self.lease_days)

		# create instances
		# see https://github.com/ChameleonCloud/python-chi/blob/82c926f5dd50501b6d893ed33ebd48ed7f1565a1/chi/server.py
		if True:
			logging.info(f"Creating server...")
			__reservation_id = get_node_reservation(uid)
			__server = create_server(
				uid, 
				reservation_id=__reservation_id,
				image_name=self.image_name,
				network_name=self.network_name,
				count=self.num,
				key_name=self.ssh_key_name
			)
			logging.info(f"server created {__server}")

		# wait for node to come up
		if True:
			for I in range(self.num):
				while True:
					try:
						name=f"{uid}-{I+1}" if self.num>1 else uid
						server_id = get_server_id(name)
						logging.info(f"wait for server name={name} num={I}/{self.num} id={server_id} (NOTE: can take 30 minutes)...")
						server=Server(server_id)
						server.wait()
						break 
					except:
						continue
				
				logging.info(f"server {name} {I}/{self.num} wait() ready")

		# ips (the first are assigned to VM, extra will be elastic ip)
		if True:
			for I in range(self.num_ips):
				if I<self.num:
					logging.info(f"Getting ip for node {I}/{self.num}...")
					name=f"{uid}-{I+1}" if self.num>1 else uid
					server_id = get_server_id(name)
					ip = associate_floating_ip(server_id)  
					logging.info(f"Got {ip} for node {I}/{self.num}, now waiting for ssh port...")
					wait_for_tcp(ip, port=22)  
					logging.info(f"ssh ready {I}/{self.num}") 
				else:
					logging.info(f"Waiting for extra elastic ips...")
					ip=get_free_floating_ip(allocate=True) 
					floating_ip=ip["floating_ip_address"]
					logging.info(f"Got extra ip {floating_ip}")

		return self.getNodes(args)

	# getNodes
	def getNodes(self, args):

		uid=args[0]
		instances=list_servers()
		
		try:
			floating_ips=set(get_reserved_floating_ips(uid))
		except:
			floating_ips=[]

		# part of the reserved floating ips are for instances
		ret=[]
		for server in instances:
			# pprint(server.__dict__)
			node_ip="0.0.0.0"
			for k,l in server.__dict__["addresses"].items():
				for net in l:
					if net["OS-EXT-IPS:type"]=="floating":
						addr=net["addr"]
						node_ip=addr
						floating_ips.remove(addr)

			ret.append({
				"type" : "node",
				"public_ip" : node_ip,
				"name": server.name,
				"ssh-key-name": self.ssh_key_name,
				"ssh-username": self.ssh_username,
				"ssh-key-filename": self.ssh_key_filename,  
				"ssh-command" : f"ssh  -o StrictHostKeyChecking=no -i {self.ssh_key_filename} {self.ssh_username}@{node_ip}"	 
			})

		# part are pure ip for for load balancing
		for ip in floating_ips:
			ret.append({
				"type" : "elastic_ip",
				"public_ip" : ip,
			})

		return ret

	# deleteNodes
	def deleteNodes(self, args):
		uid=args[0]
		logging.info(f"destroyNodes")
		for I in range(self.num):
			name=f"{uid}-{I+1}" if self.num>1 else uid
			server_id = get_server_id(name)
			logging.info(f"Deleting instance {I}/{self.num}..")
			delete_server(server_id)
			logging.info(f"Deleted instance {I}/{self.num}")
		# NOTE: floating IPs are removed after the lease removal
		delete_lease(uid)
		return True


