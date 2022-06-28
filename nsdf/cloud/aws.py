from ast import excepthandler
import os,sys,argparse
from pprint import pprint
import logging

import os,sys,struct,base64,time,socket,argparse
import boto3

from .utils import Check
from .base_ec2 import BaseEc2

# //////////////////////////////////////////////////////////////////////
class AmazonEC2(BaseEc2):

	# constructor
	def __init__(self, config):

		logging.info(f"AmazonEC2")
		super().__init__(config)
		
		self.conn=boto3.resource('ec2',
			aws_access_key_id=config["access-key"], 
			aws_secret_access_key=config["secret-access-key"],
			region_name=config["region"])

		self.instance_type=self.config["instance-type"]
		self.cidr_block=self.config["cidr-block"]
		self.image_id=self.config["image-id"]
		
		logging.info(f"\t [instance_type={self.instance_type}]")
		logging.info(f"\t [cidr_block={self.cidr_block}]")
		logging.info(f"\t [image={self.image_id}]")

	# getRegions
	def getRegions(self,args=None):
		client = self.conn.meta.client
		return [region['RegionName'] for region in client.describe_regions()['Regions']]

	# getVpcs (in single region)
	def getVpcs(self,args=None):
		vpcs = list(self.conn.vpcs.filter())
		return [vpc.id for vpc in vpcs]

	# see https://gist.github.com/alberto-morales/b6d7719763f483185db27289d51f8ec5
	def destroyVPC(self, vpc_id):

		if not vpc_id:
			return

		client = self.conn.meta.client
		
		logging.info(f"Deleting vpc {vpc_id}")
		vpc=self.conn.Vpc(vpc_id)

		logging.info(f"disassociate EIPs and release EIPs from EC2 instances")
		for subnet in vpc.subnets.all():
			for instance in subnet.instances.all():
				filters = [{"Name": "instance-id", "Values": [instance.id]}]
				eips = client.describe_addresses(Filters=filters)["Addresses"]
				for eip in eips:
					client.disassociate_address(AssociationId=eip["AssociationId"])
					client.release_address(AllocationId=eip["AllocationId"])

		logging.info(f"delete running instances")
		filters = [
			{"Name": "instance-state-name", "Values": ["running"]},
			{"Name": "vpc-id", "Values": [vpc_id]},
		]
		ec2_instances = client.describe_instances(Filters=filters)
		instance_ids = []
		for reservation in ec2_instances["Reservations"]:
			instance_ids += [instance["InstanceId"] for instance in reservation["Instances"]]

		
		logging.info(f"wait for instance to finish {instance_ids}")
		if instance_ids:
			waiter = client.get_waiter("instance_terminated")
			client.terminate_instances(InstanceIds=instance_ids)
			waiter.wait(InstanceIds=instance_ids)

		# note - this only handles vpc attachments, not vpn
		logging.info(f"delete transit gateway attachment for this vpc")
		for attachment in client.describe_transit_gateway_attachments()["TransitGatewayAttachments"]:
			if attachment["ResourceId"] == vpc_id:
				client.delete_transit_gateway_vpc_attachment(TransitGatewayAttachmentId=attachment["TransitGatewayAttachmentId"])

		logging.info(f"delete NAT Gateways")
		# attached ENIs are automatically deleted
		# EIPs are disassociated but not released
		filters = [{"Name": "vpc-id", "Values": [vpc_id]}]
		for nat_gateway in client.describe_nat_gateways(Filters=filters)["NatGateways"]:
			client.delete_nat_gateway(NatGatewayId=nat_gateway["NatGatewayId"])

		logging.info(f"detach default dhcp_options if associated with the vpc")
		dhcp_options_default = self.conn.DhcpOptions("default")
		if dhcp_options_default:
			dhcp_options_default.associate_with_vpc(VpcId=vpc.id)

		logging.info(f"delete any vpc peering connections")
		for vpc_peer in client.describe_vpc_peering_connections()["VpcPeeringConnections"]:
			if vpc_peer["AccepterVpcInfo"]["VpcId"] == vpc_id:
				self.conn.VpcPeeringConnection(vpc_peer["VpcPeeringConnectionId"]).delete()
			if vpc_peer["RequesterVpcInfo"]["VpcId"] == vpc_id:
				self.conn.VpcPeeringConnection(vpc_peer["VpcPeeringConnectionId"]).delete()

		logging.info(f"delete endpoints")
		for ep in client.describe_vpc_endpoints(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["VpcEndpoints"]:
			client.delete_vpc_endpoints(VpcEndpointIds=[ep["VpcEndpointId"]])

		logging.info(f"delete custom security groups")
		for sg in vpc.security_groups.all():
			if sg.group_name != "default":
				sg.delete()

		logging.info(f"delete custom NACLs")
		for netacl in vpc.network_acls.all():
			if not netacl.is_default:
				netacl.delete()

		logging.info(f"ensure ENIs are deleted before proceding")
		timeout = time.time() + 300
		filter = [{"Name": "vpc-id", "Values": [vpc_id]}]
		reached_timeout = True
		while time.time() < timeout:
			if not client.describe_network_interfaces(Filters=filters)["NetworkInterfaces"]:
				logging.info(f"no ENIs remaining")
				reached_timeout = False
				break
			else:
				logging.info(f"waiting on ENIs to delete")
				time.sleep(30)

		if reached_timeout:
			logging.info(f"ENI deletion timed out")

		logging.info(f"delete subnets")
		for subnet in vpc.subnets.all():
			for interface in subnet.network_interfaces.all():
				interface.delete()
			subnet.delete()

		logging.info(f"Delete routes, associations, and routing tables")
		filter = [{"Name": "vpc-id", "Values": [vpc_id]}]
		route_tables = client.describe_route_tables(Filters=filter)["RouteTables"]
		for route_table in route_tables:
			for route in route_table["Routes"]:
				if route["Origin"] == "CreateRoute":
					client.delete_route(RouteTableId=route_table["RouteTableId"],DestinationCidrBlock=route["DestinationCidrBlock"],)
				for association in route_table["Associations"]:
					if not association["Main"]:
						try:
							client.disassociate_route_table(AssociationId=association["RouteTableAssociationId"])
						except:
							pass
						try:
							client.delete_route_table(RouteTableId=route_table["RouteTableId"])
						except:
							pass
		
		logging.info(f"delete routing tables without associations")
		for route_table in route_tables:
			if route_table["Associations"] == []:
				client.delete_route_table(RouteTableId=route_table["RouteTableId"])

		logging.info(f"destroy NAT gateways")
		filters = [{"Name": "vpc-id", "Values": [vpc_id]}]
		nat_gateway_ids = [
			nat_gateway["NatGatewayId"]
			for
			nat_gateway in client.describe_nat_gateways(Filters=filters)["NatGateways"]
		]
		for nat_gateway_id in nat_gateway_ids:
			client.delete_nat_gateway(NatGatewayId=nat_gateway_id)

		logging.info(f"detach and delete all IGWs associated with the vpc")
		for gw in vpc.internet_gateways.all():
			vpc.detach_internet_gateway(InternetGatewayId=gw.id)
			gw.delete()

		client.delete_vpc(VpcId=vpc_id)
		logging.info(f"deleted Vpc {vpc.id}") 

	# getVPCName
	def getVPCName(self, vpc_id):
		vpc=self.conn.Vpc(vpc_id)
		if not vpc.tags:
			return 
		for it in vpc.tags:
			if it["Key"]=="Name": 
				return it["Value"]
		return ""

	# getInstancesInVPC
	def getInstancesInVPC(self, vpc_id):

		ec2_instances = self.conn.meta.client.describe_instances(Filters=[
			{"Name": "instance-state-name", "Values": ["running"]},
			{"Name": "vpc-id", "Values": [vpc_id]},
		])

		ret=[]
		for reservation in ec2_instances["Reservations"]:
			for id in [instance["InstanceId"] for instance in reservation["Instances"]]:
				instance=self.conn.Instance(id)
				public_ip=instance.public_ip_address
				item={
					"id": id,
					"type" : "node",
					"public_ip":public_ip,
					"instance_type" : instance.instance_type,
					"region": self.region,
					"ssh-key-name": self.ssh_key_name,
					"ssh-username": self.ssh_username,
					"ssh-key-filename": self.ssh_key_filename,
					"ssh-command" : f"ssh  -o StrictHostKeyChecking=no -i {self.ssh_key_filename} {self.ssh_username}@{public_ip}"   
				}
				ret.append(item)
		
		return ret

	# createNodes
	def createNodes(self,args):

		uid=args[0]
		Check(uid)
		Check(self.num_ips==0 or self.num_ips<=self.num) # todo additional IPs

		logging.info(f"createNodes {uid}")
		Check(self.num>0 and self.num<100) 

		client = self.conn.meta.client

		vpc_id = client.create_vpc(CidrBlock=self.cidr_block)["Vpc"]["VpcId"]
		client.get_waiter("vpc_exists").wait(VpcIds=[vpc_id])
		vpc=self.conn.Vpc(vpc_id)
		vpc.create_tags(Tags=[{
			"Key": "Name", 
			"Value": f"{uid}"
		}])

		# enable public dns hostname so that we can SSH into it later
		vpc.modify_attribute(EnableDnsSupport   = { 'Value': True } )
		vpc.modify_attribute(EnableDnsHostnames = { 'Value': True } )

		# create subnet
		subnet = self.conn.create_subnet(CidrBlock=self.cidr_block, VpcId=vpc.id,  AvailabilityZone=self.region + "a")
		logging.info(f"create subnet {subnet.id}")

		# create security group 
		sg = self.conn.create_security_group(GroupName=f"{uid}-sg", Description='my-security-group', VpcId=vpc.id)
		logging.info(f"created security groupd {sg.id}")

		if True:
			sg.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=0,  ToPort=65535)
		else:
			for port in self.ports:
				sg.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=port,  ToPort=port)

		# for docker mapping
		#  logging.info(f"Vpc Authorizing also FromPort=8000 ToPort=10000 (for debuggin)")
		#  sg.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=8000,  ToPort=10000)

		# attach internet gateway
		ig=self.conn.create_internet_gateway()
		vpc.attach_internet_gateway(InternetGatewayId=ig.id)
		logging.info(f"created and attached internet gateway {ig.id}")

		# ***  create a route table and a public route *** 
		rt = vpc.create_route_table()
		rt.associate_with_subnet(SubnetId=subnet.id)
		rt.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=ig.id)
		logging.info(f"created route table {rt.id}")

		# create instance
		# us-east-1 - todo for other regions
		# TODO....
		username="ubuntu" # depends on os

		# adding a public ip to any
		instances  = self.conn.create_instances(
			ImageId=self.image_id, 
			InstanceType=self.instance_type,
			MinCount=self.num,
			MaxCount=self.num,
			KeyName=self.ssh_key_name,
			UserData="",
			NetworkInterfaces=[{"SubnetId": subnet.id,"DeviceIndex": 0,"AssociatePublicIpAddress": True, "Groups": [sg.id],}],
			TagSpecifications=[{'ResourceType': 'instance','Tags': [{'Key': 'Name','Value': uid},]}]
		)
		logging.info(f"created instance")
				
		# wait for all the instances to come up
		logging.info(f"waiting virtual machines to come up")
		ret=[]
		for instance in instances:
			instance.wait_until_running()
			instance.reload()
			if 22 in self.ports:
				while True:
					if socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex((instance.public_dns_name,22))==0: 
						break
					logging.info(f"Waiting for port 22 to come up...")
					time.sleep(1)
				logging.info(f"instance ready id={instance.id}")

		return self.getNodes(args)

	# getNodes
	def getNodes(self, args):
		uid=args[0]
		Check(uid)
		ret=[]
		for vpc_id in self.getVpcs():
			vpc_name=self.getVPCName(vpc_id)
			if vpc_name and vpc_name==uid:
				ret=ret+self.getInstancesInVPC(vpc_id)
		return ret

	# destroyNodes
	def deleteNodes(self,args):
		uid=args[0]
		Check(uid!="")
		for vpc_id in self.getVpcs():
			vpc_name=self.getVPCName(vpc_id)
			if vpc_name==uid: 
				self.destroyVPC(vpc_id)



