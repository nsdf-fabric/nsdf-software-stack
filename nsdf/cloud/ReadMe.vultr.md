# Vultr setup

Login into the [Vultr Data Portal](my.vultr.com).

## Create an API secret

Click on your username and select `API/Enable API`. Copy the `API Key` somewhere. And in the *Access Control section* Add `Any IPv4` as allowed subnets.

**Remember to disable the API when finished and to remove subnets too**

## Generate ssh key and add to the portal

Generate an ssh key:

```
if [ ! -f ~/.ssh/id_nsdf ] ; then
  ssh-keygen -t rsa -f ~/.ssh/id_nsdf -N ""
fi
```

Go to the Vulr [Manage SSH keys](https://www.cloudlab.us/ssh-keys.php) and add your `id_nsdf.pub` key:

- Name: `id_nsdf`

- Content: *copy the id_nsdf.pub content here*

## Update your vault file

Add one item to your `~/.nsdf/vault/vault.yml` file (change values as needed; for example you may need to change the `api-key`):

```
nsdf-cloud-vultr:
  class: VultrEc2
  api-key: XXXXX
  num: 1
  VPSPLANID: 201  # this plan is '1024 MB RAM,25 GB SSD,1.00 TB BW'
  OSID: 387 # this is Ubuntu 20.04 x64 
  region: New Jersey
  ssh-username: root
  ssh-key-filename: ~/.ssh/id_nsdf
  ssh-key-name: id_nsdf
```

# Examples

Create new nodes`:

```
ACCOUNT=nsdf-cloud-vultr
python3 -m nsdf.cloud $ACCOUNT create nodes test1 --num 1 
```

List of nodes:

```
python3 -m nsdf.cloud $ACCOUNT get nodes test1 
```

Delete nodes:

```
python3 -m nsdf.cloud $ACCOUNT delete nodes test1 
```

Other useful commands:

```
# if you want to change the VM (i.e. VPSPLANID)
python3 -m nsdf.cloud $ACCOUNT get plans

# if you want to change the OS
python3 -m nsdf.cloud $ACCOUNT get os

# if you want to change the region
python3 -m nsdf.cloud $ACCOUNT get regions
```
