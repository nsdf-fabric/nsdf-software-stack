# Node setup


```
sudo python3 -m pip install --upgrade pip

sudo python3 -m pip install  \
   requests \
   urllib3 \
   asyncssh \
   pendulum \
   cryptography \
   awscli  \
   boto3 \
   distributed \
   dask[complete]  \
   prefect[viz]   \
   BeautifulSoup4 \
   imageio \
   scikit-image \
   numpy \
   scipy \
   matplotlib 

sudo python3 -m pip install --upgrade urllib3
sudo python3 -m pip install imageio
sudo python3 -m pip install clickhouse-driver

# create local storage
sudo mkdir       /srv/nvme0/nsdf 
sudo chown $USER /srv/nvme0/nsdf

# clone vault
cp ~/.nsdf/vault/id_nsdf ~/.ssh
chmod 700 ~/.ssh/id_nsdf 
export GIT_SSH_COMMAND="ssh -i ~/.ssh/id_nsdf"
git clone git@github.com:nsdf-fabric/vault.git ~/.nsdf/

pushd ~/.nsdf/vault/ && git checkout -f  && git pull && popd

# create AWS credentials
mkdir ~/.aws
cp ~/.nsdf/vault/aws_config ~/.aws/config
cp ~/.nsdf/vault/aws_credentials ~/.aws/credentials
more ~/.aws/config

# open firewall ports
#    `curl ifconfig.me` to get the ip
#    `ifconfig` to get the netmask
sudo ufw allow from 155.101.6.0/24 to any port nfs
sudo ufw status

# server side (allow the export to all hosts, then the firewall will limit the connections)
sudo apt install -y nfs-kernel-server nfs-common
DIR=/mnt/shared
sudo mkdir -p $DIR && sudo chown $USER $DIR && sudo chmod 700 $DIR

echo "${DIR} *(rw,sync,no_subtree_check)" | sudo tee -a /etc/exports
more /etc/exports
# sudo vi /etc/exports
sudo exportfs -ra
sudo showmount -e

# client side
sudo apt install -y nfs-common net-tools
DIR=/mnt/shared
SERVER=nsdf01
sudo mkdir -p $DIR && sudo chown $USER $DIR && sudo chmod 700 $DIR
sudo mount --verbose -t nfs $SERVER:${DIR} ${DIR}
echo "$SERVER:${DIR} ${DIR} nfs defaults 0 0" | sudo tee -a /etc/fstab
sudo  mount | grep $DIR

cd /mnt/shared/nsdf
git clone git@github.com:nsdf-fabric/nsdf-software-stack.git
cd nsdf-software-stack
```

# Copy objects

```
#!/bin/bash

export NUM_WORKERS=6
export NUM_CONNECTIONS=128
export SRC="s3://Pania_2021Q3_in_situ_data?profile=wasabi&num-connections=$NUM_CONNECTIONS"
export DST="s3://utah/buckets/Pania_2021Q3_in_situ_data?profile=sealstorage&num-connections=$NUM_CONNECTIONS&no-verify-ssl"

while [[ 1 == 1 ]] ; do  
	python3 -m nsdf.s3 copy-objects ${SRC} ${DST}
done
```

# New upload

See `upload.py`



