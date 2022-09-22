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
cp ~/.nsdf/vault/awsaws/* ~/.aws/
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

# OpenVisus (modvisus)


See https://docs.google.com/spreadsheets/d/11dw63aS7NJA4px0yp_IZB1Yq79JvXsl7/edit#gid=1779202315

```
ssh nsdf1.scu.utah.edu

sudo apt install nfs-common

sudo mkdir -p /usr/sci/cedmav
sudo mount -t nfs 155.98.58.116:/cedmav  /usr/sci/cedmav

sudo mkdir -p /usr/sci/brain
sudo mount -t nfs 155.98.58.116:/sci/brain /usr/sci/brain

rm datasets.txt
nohup find /usr/sci/cedmav -iname "*.idx" 2>/dev/null >> datasets.txt
nohup find /usr/sci/brain  -iname "*.idx" 2>/dev/null >> datasets.txt
```

# Material Science Data

See `material-science-upload.py`


# OpenVisus (arco)

Example about how to create an arco version of an existing db

```
# convert locally to ARCO format
python3 -m nsdf.convert copy-dataset --arco 1mb  /mnt/c/data/visus-dataset/2kbit1/modvisus/visus.idx /mnt/c/data/visus-dataset/2kbit1/1mb/visus.idx 
python3 -m nsdf.convert compress-dataset --compression zip --num-threads 32 /mnt/c/data/2kbit1/1mb/visus.idx 

# copy ARCO to the cloud
# aws s3  --no-verify-ssl --endpoint-url <endpoint> --profile <profile> cp  --if-size-differ <src> s3://<dst-path>

AWS_PROFILE=chpc s5cmd --no-verify-ssl -log=debug "$@" --numworkers 64 --endpoint-url https://pando-rgw01.chpc.utah.edu cp --if-size-differ \
   "/mnt/c/data/visus-datasets/2kbit1/1mb/*" "s3://nsdf/visus-datasets/2kbit1/1mb/"

```


# NASA Satellite data (?)

Links:

- https://www.matecdev.com/posts/download-remote-sensing-data-python.html
- https://www.geosage.com/products/spectral_transformer/Sentinel2/SpectralDiscoveryForSentinel2.pdf
- https://www.matecdev.com/posts/download-remote-sensing-data-python.html
- https://ladsweb.modaps.eosdis.nasa.gov/tools-and-services/data-download-scripts/


Repository with NASA data
- https://e4ftl01.cr.usgs.gov/


All AWS public data with `RequesterPays`:

```
git clone https://github.com/awslabs/open-data-registry.git
cd open-data-registry/
git grep --files-with-matches "RequesterPays: True"


# https://github.com/awslabs/open-data-registry/blob/main/datasets/cbers.yaml
# magery acquired by the China-Brazil Earth Resources Satellite (CBERS), 4 and 4A.
https://github.com/awslabs/open-data-registry/blob/main/datasets/cbers.yaml

# https://github.com/awslabs/open-data-registry/blob/main/datasets/hsip-lidar-us-cities.yaml
# The U.S. Cities elevation data collection program supported the US Department of Homeland Security Homeland Security and Infrastructure Program (HSIP). 
https://github.com/awslabs/open-data-registry/blob/main/datasets/hsip-lidar-us-cities.yaml

# https://github.com/awslabs/open-data-registry/blob/main/datasets/modis-astraea.yaml
# data from the Moderate Resolution Imaging Spectroradiometer (MODIS), managed by the U.S. Geological Survey and NASA.
https://github.com/awslabs/open-data-registry/blob/main/datasets/modis-astraea.yaml

# https://github.com/awslabs/open-data-registry/blob/main/datasets/naip.yaml
# The National Agriculture Imagery Program (NAIP) acquires aerial imagery during the agricultural growing seasons in the continental U.S. 
https://github.com/awslabs/open-data-registry/blob/main/datasets/naip.yaml

# https://github.com/awslabs/open-data-registry/blob/main/datasets/sentinel-1.yaml
# "[Sentinel-1](https://sentinel.esa.int/web/sentinel/missions/sentinel-1) is a pair of European radar imaging (SAR) satellites launched in 2014 and 2016.
https://github.com/awslabs/open-data-registry/blob/main/datasets/sentinel-1.yaml

# https://github.com/awslabs/open-data-registry/blob/main/datasets/sentinel-2.yaml
# The [Sentinel-2 mission](https://sentinel.esa.int/web/sentinel/missions/sentinel-2) is a land monitoring 
# constellation of two satellites that provide high resolution optical imagery 
https://github.com/awslabs/open-data-registry/blob/main/datasets/sentinel-2.yaml

# (NASA) https://github.com/awslabs/open-data-registry/blob/main/datasets/usgs-landsat.yaml
# This joint NASA/USGS program provides the longest continuous space-based record of 
# Earth’s land in existence. Every day, Landsat satellites provide essential information 
# to help land managers and policy makers make wise decisions about our resources and our environment.
# Data is provided for Landsats 1, 2, 3, 4, 5, 7, and 8.
https://github.com/awslabs/open-data-registry/blob/main/datasets/usgs-landsat.yaml

# https://github.com/awslabs/open-data-registry/blob/main/datasets/usgs-lidar.yaml
# The goal of the [USGS 3D Elevation Program ](https://www.usgs.gov/core-science-systems/ngp/3dep) (3DEP) is to collect elevation data in the form of light detection and ranging (LiDAR) data
https://github.com/awslabs/open-data-registry/blob/main/datasets/usgs-lidar.yaml
```

Command to collect statistics:

```

# with AWS cli tools
aws s3 ls --request-payer requester s3://usgs-landsat/collection02/
aws s3 ls --request-payer requester --summarize --recursive --human-readable s3://usgs-landsat/collection02/

# with s5cmd
export AWS_REGION=us-west-2
s5cmd --endpoint-url=https://s3.us-west-2.amazonaws.com --request-payer=requester --log trace --numworkers=256 ls --recursive "s3://usgs-landsat/collection02/"
s5cmd --endpoint-url=https://s3.us-west-2.amazonaws.com --request-payer=requester --log trace --numworkers=256 du "s3://usgs-landsat/collection02/*"
```