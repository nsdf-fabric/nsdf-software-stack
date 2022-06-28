
# NSDF Cloud Examples

Create new nodes:

```
# python3 -m pip install --user python-chi



# https://www.cloudlab.us/portal-hardware.php
# m400        -  8 coresARM X-Gene 1 at 2.4Ghz  - 64 GB - 1x120GB SATA3       - 10Gbit
# c6525-25g   - 16-core AMD 7302P    at 3.00GHz - 128GB - 2x480GB 6G SATA SSD - 2x mellanox 25Gb
# c6525-100g  - 24-core AMD 7402P    at 2.80GHz - 128GB - 2x1.6TB NVMe SSD    - 1x mellanox 25Gb + 1x mellanox 100Gb
ACCOUNT=nsdf-cloud-cloudlab
NAME=nsdf-node
HARDWARE_TYPE=c6525-25g 
python3 -m nsdf.cloud $ACCOUNT create nodes $NAME --num 2 --hardware-type $HARDWARE_TYPE
# python3 -m nsdf.cloud $ACCOUNT extend nodes $NAME --num 2 --hardware-type $HARDWARE_TYPE
```

List of nodes:

```
python3 -m nsdf.cloud $ACCOUNT get nodes test1 
```
2
Extend lease of nodes:

```
python3 -m nsdf.cloud $ACCOUNT extend nodes test1 
```

Delete nodes:

```
python3 -m nsdf.cloud $ACCOUNT delete nodes test1 
```

## CloudLab setup

Links:

- https://groups.google.com/forum/#!forum/cloudlab-users
- [CloudLab - Show Profile](https://www.cloudlab.us/show-profile.php?uuid=bdca59db-aa6a-11e9-8677-e4434b2381fc)
- [CloudLab - Login](https://www.cloudlab.us/user-dashboard.php)
- 

You need the `portal-tools` python package:

```
git -c http.sslVerify=false clone https://gitlab.flux.utah.edu/stoller/portal-tools.git 

pushd portal-tools 
python3 setup.py install --user 
popd
rm -Rf portal-tools
```

Login into the [CloudLab Portal](https://www.cloudlab.us/login.php)

## Generate ssh key

Generate an ssh key:

```
if [ ! -f ~/.ssh/id_nsdf ] ; then
  ssh-keygen -t rsa -f ~/.ssh/id_nsdf -N ""
fi
```

Go to [Manage SSH keys](https://www.cloudlab.us/ssh-keys.php) and add your `id_nsdf.pub` key content.

## Download PEM file

Click on your username and *download credentials*; you should get a `cloudlab.pem` file that you need to add to your `~/.ssh` directory.

To remove the passphrase from the PEM  file (this is needed from programmatically creation of VMs):

```
pushd ~/.ssh
mv cloudlab.pem cloudlab.pem.source

# this is the private key
openssl rsa  -in cloudlab.pem.source >  cloudlab.pem 
# *** ENTER your CloudLab password ***

# this is the certificate (APPEND mode)
openssl x509 -in cloudlab.pem.source >> cloudlab.pem 

popd
```

## Create new profile

Create a new profile with name `nsdf-profile`:

```
"""NSDF Variable number of nodes in a lan. . 

Instructions:
see http://docs.cloudlab.us/
"""

"""
import geni.portal as portal
import geni.rspec.pg as pg
import geni.rspec.emulab as emulab
from geni.rspec.igext import AddressPool

pc = portal.Context()
request = pc.makeRequestRSpec()

pc.defineParameter("nodeCount", "Number of Nodes",   portal.ParameterType.INTEGER, 4,    longDescription="number of nodes")
pc.defineParameter("hardware_type", "Hardware Type", portal.ParameterType.STRING, "m400", longDescription="hardware type")

params = pc.bindParameters()
pc.verifyParameters()

nodeCount=params.nodeCount
hardware_type=params.hardware_type

lan = request.LAN("lan")
# lan.bandwidth = 10000000 # 10Gbit/sec 

# Request 1 routable ip addresses for MetalLB
addressPool = AddressPool('addressPool', int(1))
request.addResource(addressPool)

for I in range(nodeCount):
	name = "node{}".format(I+1)
	node = request.RawPC(name) # request.XenVM(name)
	node.component_manager_id = "urn:publicid:IDN+utah.cloudlab.us+authority+cm"
	node.hardware_type=hardware_type 
	
	node.disk_image = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU20-64-STD"
	iface = node.addInterface("eth1")
	
	# this breaks ssh -i ...?
	#iface.addAddress(pg.IPv4Address( "192.168.1.{}".format(I+1), "255.255.255.0"))
	
	lan.addInterface(iface)
	
	# # get max size of available disks (see https://groups.google.com/g/cloudlab-users/c/9IUzmLk_fHc)
	bs = node.Blockstore(name + "-bs", "/mnt/data")
	bs.size = "0" 

pc.printRequestRSpec(request)
```

## Update your vault file

Add one item to your `~/.nsdf/vault/vault.yml` file (change values as needed; for example you may need to change the `project-name`, `profile-name`,`ssh-username`):

```
nsdf-cloud-cloudlab:
  class: CloudLabEc2
  cloud-url: https://cloudlab.us/
  certificate: ~/.ssh/cloudlab.pem
  project-name: nsdf-testbed
  profile-name: nsdf-profile
  num: 1
  ssh-username: scorzell
  ssh-key-filename: ~/.ssh/id_nsdf
```
