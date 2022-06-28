# See https://gitlab.flux.utah.edu/stoller/portal-tools/-/tree/master

import os, sys, time, json
from re import I
from posixpath import expanduser
from pprint import pprint
import bs4,socket
import logging

import emulab_sslxmlrpc
import emulab_sslxmlrpc.client
import emulab_sslxmlrpc.client.api as api
import emulab_sslxmlrpc.xmlrpc as xmlrpc

from .utils import Check
from .base_ec2 import BaseEc2

# for HTML parsing
from bs4 import BeautifulSoup


# ///////////////////////////////////////////////////////////////////////////////////
class CloudLabEc2(BaseEc2):

	# constructor
	def __init__(self, config):
		
		logging.info("CloudLabEc2")
		super().__init__(config)
		self.config=config

		certificate=os.path.expanduser(config["certificate"])
		Check(os.path.isfile(certificate),f"cannot find certificate file {certificate}")

		self.conn = xmlrpc.EmulabXMLRPC({
			"debug" : 0,
			"impotent" : 0,
			"verify"   : 0,
			"certificate" : certificate 
		}) 

		self.project_name=self.config.get("project-name","nsdf-testbed")
		self.profile_name=self.config.get("profile-name","nsdf-profile")
		self.hardware_type=self.config.get("hardware-type","m400")

		logging.info(f"\t [project-name={self.project_name}]")
		logging.info(f"\t [profile-name={self.profile_name}]")	 
		logging.info(f"\t [hardware-type={self.hardware_type}]")	

	# getNodes
	def getNodes(self,args):

		uid=args[0]

		(exitval,response) = api.experimentManifests(self.conn, {"experiment" : f"{self.project_name},{uid}",}).apply()
		Check(exitval==0,f"failed to getNodes: experimentManifests returned {exitval}\nCODE:{response.code}\nVALUE:{response.value}\nOUTPUT: {response.output}")

		manifest = json.loads(response.value)
		manifest=manifest[list(manifest.keys())[0]]
		manifest=bs4.BeautifulSoup(manifest,"xml")

		# this are real nodes
		ret=[]
		for it in manifest.find_all("node"):
			ip4=it.find("host")["ipv4"]
			ret.append({
				"type" : "node",
				"public_ip" : ip4,
				"ssh-username": self.ssh_username,
				"ssh-key-filename": self.ssh_key_filename, 
				"ssh-command" : f"ssh  -o StrictHostKeyChecking=no -i {self.ssh_key_filename} {self.ssh_username}@{ip4}"				  
			})

		# this is an extra public ip for load balancing
		for it in manifest.find("emulab:routable_pool"):
			ip4=it["address"]
			ret.append({
				"type" : "elastic_ip",
				"public_ip" : ip4,
			})

		return ret

	# createNodes
	def createNodes(self, args):

		uid=args[0]

		Check(self.num>0 and self.num<100) # safety check

		bindings={
			"nodeCount" : f"{self.num}",
			"hardware_type" : f"{self.hardware_type}"
		}

		conf={
			"profile" : f"{self.project_name},{self.profile_name}",
			"proj"	: f"{self.project_name}",
			"name"	: f"{uid}",
			'bindings' : """{"nodeCount" : "$num", "hardware_type" : "$hardware_type"}""".replace("$num",str(self.num)).replace("$hardware_type",str(self.hardware_type)),
		}

		if True:
			logging.info(f"creating nodes")
			(exitval,response) = api.startExperiment(self.conn,conf).apply()
			Check(exitval==0,f"startExperiment failed with exitval={exitval} and response {response.output}")

		if True:
			logging.info(f"Experiment started, waiting for ready status...")
			while True:
				(exitval,response) = api.experimentStatus(self.conn, {
					"experiment" : f"{self.project_name},{uid}",
					"asjson" : True
				}).apply()

				status,total,finished="",0,0
				if exitval:
					if response.value in [api.GENIRESPONSE_REFUSED, api.GENIRESPONSE_NETWORK_ERROR ,api.GENIRESPONSE_BUSY]:
						pass # need to wait a littke
					else:
						Check(False, f"experimentStatus failed with exitval={exitval} and response {response}")
				else:
					body = json.loads(response.value)
					status=body["status"]
					Check(status!="failed", f"experimentStatus failed with exitval={exitval} and response {response.output}")

					total	= body["execute_status"]["total"   ] if "execute_status" in body else 1
					finished = body["execute_status"]["finished"] if "execute_status" in body else 1

				logging.info(f"status={status} total={total} finished={finished}")
				if status=="ready" and total==finished:  break
				time.sleep(10)

		ret=self.getNodes(args)
		for node in ret:
			if node["type"]!="node":  continue
			ip4=node["public_ip"]
			logging.info(f"waiting for ssh port to come up ip4={ip4}...")
			while True:
				if socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex((ip4,22))==0: break
				logging.info(f"still waiting...")
				time.sleep(5)
			logging.info(f"instance ready")

		return ret

	# extendNodes
	def extendNodes(self, args):
		uid=args[0]
		logging.info(F"extend_instances {self.project_name},{uid}")
		(exitval,response)=api.extendExperiment (self.conn,{
				"experiment" : f"{self.project_name},{uid}",
				"wanted": "72", # hours?
				"reason": "I need this for another day please (nsdf-testbed automatic script to keep the node alive)",
				"asjson" : True
			}).apply()
		Check(exitval==0,f" extendExperiment  failed with exitval={exitval} {response}")
		return True

	# deleteNodes
	def deleteNodes(self, args):
		uid=args[0]
		logging.info(F"deleteNodes")
		(exitval,response)=api.terminateExperiment(self.conn,{
					"experiment" : f"{self.project_name},{uid}",
					"asjson" : True
			}).apply()
		Check(exitval==0,f"terminateExperiment failed with exitval={exitval} and response {response.output}")
