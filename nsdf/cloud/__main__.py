
import os,sys,logging,json,types
from distutils.command.check import check
from pprint import pprint,pformat

from .utils import *
import json

# all the automation classes here
from .aws       import AmazonEC2
from .chameleon import ChameleonEC2
from .cloudlab  import CloudLabEc2
from .vultr      import VultrEc2
from .jetstream  import JetStreamEc2

# //////////////////////////////////////////////////////////////
def CreateAnsibleInventory(uid, nodes):
	username=nodes[0]["ssh-username"]
	key_filename=nodes[0]["ssh-key-filename"]	
	hosts="\n    ".join([it['public_ip'] for it in nodes if it.get('type','node')=='node'])

	return f"""


{uid}:
  hosts:
    {hosts}
  vars:
    ansible_connection: ssh
    ansible_user: {username}
    ansible_ssh_private_key_file: {key_filename}
    ansible_ssh_extra_args: '-o StrictHostKeyChecking=no'
    ssh-command: ssh -o StrictHostKeyChecking=no -i {key_filename} {username}@{nodes[0]['public_ip']}
""".strip() + "\n"

# //////////////////////////////////////////////////////////////
def CreateTiDbTopology(nodes,arch="arm64"):

	# todo, here I am assuming cloudlab
	assert arch=="arm64"

	hosts=[it['public_ip'] for it in nodes if it.get('type','node')=='node']
	pd_servers=hosts
	tidb_servers=hosts
	tikv_servers=hosts
	monitoring_servers=hosts[0:1]
	grafana_servers=hosts[0:1]
	alertmanager_servers=hosts[0:1]
	server_configs=""

	def format_list(l):
		return "".join([f"  - host: {it}\n" for it in l  ]).rstrip()

	return f"""
global:
  user: "tidb"
  ssh_port: 22
  deploy_dir: "/tidb-deploy"
  data_dir: "/tidb-data"
  arch: "arm64" # cloudlab
server_configs: {server_configs}
pd_servers:
{format_list(pd_servers)}
tidb_servers:
{format_list(tidb_servers)}
tikv_servers:
{format_list(tikv_servers)}
monitoring_servers:
{format_list(monitoring_servers)}
grafana_servers:
{format_list(grafana_servers)}
alertmanager_servers:
{format_list(alertmanager_servers)}
"""


# //////////////////////////////////////////////////////////////
def main(args):

	if not args:
		return

	# setup the logging
	logging.basicConfig(
		format='%(asctime)s %(levelname)-6s [%(filename)-12s:%(lineno)-3d] %(message)s',
		datefmt='%Y-%m-%d:%H:%M:%S',level=logging.INFO)

	target=args[0]
	args=args[1:]

	# in the ~/.nsdf/vault/vault.yaml file there should be an item with the $TARGET name
	config=GetConfig(target)

	# override by command line
	# example --region us-east-1
	I=0
	while I< len(args)-1:
		if args[I].startswith("--"):
			key,value=args[I][2:].strip(),args[I+1].strip()
			logging.info(f"Adding to config {key}={value}")
			config[key]=value
			I+=2
		else:
			I+=1

	# dangerous
	# logging.info(f"Current config:\n{pformat(config)}")

	# create the class to automatically create VMs
	Class=config.pop("class")
	logging.info(f"Class is {Class}")
	instance=eval(f"{Class}(config)")

	if args[0:2]==["create","inventory"]:
		uid,args=args[2],args[2:]
		nodes=instance.getNodes(args)
		print(CreateAnsibleInventory(uid, nodes))
		return 0

	if args[0:2]==["create","tidb-topology"]:
		uid,args=args[2],args[2:]
		nodes=instance.getNodes(args)
		print(CreateTiDbTopology(nodes))
		return 0

	if args[0:2]==["create","nodes"]:
		uid,args=args[2],args[2:]
		ret=instance.createNodes(args)
		ret=list(ret) if isinstance(ret, types.GeneratorType) else ret
		print(json.dumps(ret))
		return 0

	if args[0:2]==["get","nodes"]:
		uid,args=args[2],args[2:]
		ret=instance.getNodes(args)
		ret=list(ret) if isinstance(ret, types.GeneratorType) else ret
		print(json.dumps(ret))
		return 0

	if args[0:2]==["delete","nodes"]:
		uid,args=args[2],args[2:]
		ret=instance.deleteNodes(args)
		return 0

	# two arguments. Example: "get nodes" will call Class.getPlan(...)
	if len(args)>1:
		method_name=f"{args[0]}{args[1].title()}"
		if hasattr(instance,method_name):
			ret=eval(f"instance.{method_name}(args[2:])")
			ret=list(ret) if isinstance(ret, types.GeneratorType) else ret
			print(json.dumps(ret))
			return 0
		
	logging.info("syntax error, got",args)
	return -1
	

if __name__=="__main__":
	main(sys.argv[1:])
