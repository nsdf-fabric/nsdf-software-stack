
# Instructions


Links:
- [NYC Click Tutorial](https://tech.marksblogg.com/billion-nyc-taxi-rides-clickhouse-cluster.html)


# Setup the cluster

Install python wheels:

```

PACKAGES="materials-commons-api mysql-connector-python mdf_forge boto3 awscli imageio clickhouse-driver prefect bs4 pandas"

# if running on local host
python3 -m pip install $PACKAGES

# if running on dsk
dask_execute_code "python3 -m pip install $PACKAGES"
```

Modify the `workflow.yaml` file as needed.

Check connection:

```
INVENTORY=./ansible/inventory.ini
GROUP=all
ansible  --inventory ${INVENTORY} -m ping  ${GROUP}
```

Check S3 credentials:

```
export PYTHONPATH=$(pwd)

eval $(python3 -m nsdf.catalog export-env)
aws s3 --endpoint-url=${AWS_ENDPOINT_URL} mb $(dirname ${REMOTE}) || true
echo "hello" >> hello.bin
aws s3 --endpoint-url=${AWS_ENDPOINT_URL} cp hello.bin ${REMOTE}/
aws s3 --endpoint-url=${AWS_ENDPOINT_URL} ls ${REMOTE}/

# warm up clean the temporary directory and sync the code between workers
dask_warm_up

# run the workflow
python3 -m nsdf.catalog [--summarize]

# trask progress
while sleep 5; do aws s3 --endpoint-url=${AWS_ENDPOINT_URL} ls --recursive ${REMOTE}/csv/ | grep "\.csv" | wc -l ; done

#if you want to use `s5cmd`
# export AWS_REGION=us-east-2
# time s5cmd --log debug  ls s3://fah-public-data-covid19-absolute-free-energy/* 2>&1 1> tmp.txt
```

# (OPTIONAL) mount SSD disk

```
lsblk
sudo mkfs -t ext4 /dev/nvme1n1
sudo mkdir /vol_b
sudo mount /dev/nvme1n1 /vol_b
df -h
sudo chown -R ubuntu /vol_b
sudo chmod a+rwX /vol_b
```


# Install ClickHouse 

```
aws configure
aws configure set default.s3.max_concurrent_requests 300

ansible -m synchronize -a 'src=~/.aws dest=~/.aws' --inventory $INVENTORY $GROUP
```

(OPTIONAL) Install Java/Zookeper for clickhouse Cluster installation:

```
ansible -m shell -a "sudo apt update"                                           --inventory ${INVENTORY} ${GROUP} 
ansible -m shell -a "sudo apt install -y openjdk-8-jre openjdk-8-jdk-headless"  --inventory ${INVENTORY} ${GROUP} 

# is this needed?
# echo 'export JAVA_HOME=/usr' | sudo tee -a /etc/profile
# source /etc/profile

ansible -m shell -a "sudo apt install -y zookeeperd" --inventory ${INVENTORY} ${GROUP} 


sudo apt update
sudo apt install -y glances  mysql-client

# see https://clickhouse.com/docs/en/getting-started/install/
curl -O 'https://builds.clickhouse.com/master/amd64/clickhouse' && chmod a+x clickhouse
sudo ./clickhouse install \
  --prefix      / \
  --binary-path usr/bin \
  --config-path etc/clickhouse-server \
  --log-path    var/log/clickhouse-server \
  --data-path   var/lib/clickhouse \
  --pid-path    var/run/clickhouse-server \
  --user        clickhouse \
  --group       clickhouse 

# say `y` to allow connection from the network
# leave the password empty
# sudo vi /etc/clickhouse-server/config.xml
# sudo more /etc/clickhouse-server/users.d/default-password.xml

sudo clickhouse start
# sudo clickhouse-server --config-file=/etc/clickhouse-server/config.xml
```

# Check ClickHouse connectivity

```

# check open ports iIf you see  127.0.0.1:<port> it means it is reachable only from localhost, if you see TCP *:<port> it means it is reachable from anywhere)
sudo lsof -i -P -n | grep LISTEN | grep clickhouse
# clickhous 293708      clickhouse   68u  IPv6 1821058      0t0  TCP *:8123 (LISTEN)       HTTP client   
# clickhous 293708      clickhouse   70u  IPv6 1821062      0t0  TCP *:9005 (LISTEN)       PostgreSQL
# clickhous 293708      clickhouse   71u  IPv6 1821059      0t0  TCP *:9000 (LISTEN)       TCP/IP native client (i.e. clickhouse-client)
# clickhous 293708      clickhouse   73u  IPv6 1821060      0t0  TCP *:9009 (LISTEN)       inter-server replication
# clickhous 293708      clickhouse   74u  IPv6 1821061      0t0  TCP *:9004 (LISTEN)       mysql connections

# assuming you are logged in the host
PUBLIC_IP=$(curl ifconfig.me)

# By default, clickhouse-server has an HTTP API that listen on port 8123
# check you can reach the host (change ip as needed)
curl http://${PUBLIC_IP}:8123

# this should work since connecting from local host
clickhouse-client --host localhost --port 9000 --user default --password ""

# this should  work only if you are allowed to connect from outside
clickhouse-client --host ${PUBLIC_IP} --port 9000 --user default --password ""

# this should work since I am connecting from localhost
mysql --protocol=tcp --host=localhost --user=default --password='' --port=9004

# this should  work only if you are allowed to connect from outside
mysql --protocol=tcp --host=${PUBLIC_IP} --user=default --password='' --port=9004
```


# Create a new ClickHouse User


- uncomment the line `<!-- <access_management>1</access_management> -->` from  `/etc/clickhouse-server/users.xml`
- `sudo clickhouse restart` 
- `clickhouse-client`

```
# DANGEROUS: allow connection from ANY host
CREATE USER if not exists 'dbuser' 
IDENTIFIED WITH plaintext_password BY 'solopizza' 
HOST ANY; 

SHOW USERS;

# WITH GRANT OPTION clauses means that the user we grant the permission to, in turn has access to grant the same permission to other users
GRANT ALL PRIVILEGES ON nsdf.* TO dbuser 
WITH GRANT OPTION; 

SHOW GRANTS FOR dbuser;
```

# Populate the DB

See the `nsdf-catalog.ipynb` file






# Scraping notes:

Results on single AWS machine:  
- c5d.9xlarge 
- region=us-east-1 
- 36 vCPUs 
- 72.0 GiB	
- 900 GB NVMe SSD	  
- 10 Gigabit

Scraping numbers are with one worker only (i.e. 1 thread or 1 process)
Scraping numbers should scale almost linearly with N workers, up to the point the node has too much parallel connections.
Network performance (i.e. `byte-sent` and `byte-received`) are obtained via Python `psutil`:

```
io1 = psutil.net_io_counters()
T1=time.time()
... do the scraping...
io2 = psutil.net_io_counters()
print(f"network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")	

```

## Arecibo

I did not redo the test since they disconnected.
It was basically an HTML scraping of this web site: https://www.naic.edu/datacatalog/index.php/datasets/view/

Statistics:
- num-datasets= ??? 
- num-records=2,045,049
- tot-size=491,912,368,698,644 (491TB)
- network-upload-bytes= ???
- network-download-bytes=???
- total-seconds=???


## AWS Open Data

There is a GitHub repo (https://github.com/awslabs/open-data-registry.git) that contains all projects.
The datasets YAML files contains links to S3 buckets.
At the end the scraping is a `aws s3 ls` inside the bucket. INternally I am using Python3 boto3 library using the resful API `list_objects_v2`, single worker

Statistics
- num-datasets=398 (NOTE: I am skipping  databases not public or charged at user-side, it could be I am missing some dataset becuase the scraping had some errors)
- num-records=1,540,162,975 (1.5B)
- tot-size=45,765,462,020,085,356 (45PB)
- network-upload-bytes=160,564,493,346 (160GB)
- network-download-bytes=430,477,563,129 (430GB)
- total-seconds=294,366 (81 hours)

(partial `g_num_objects=25,156,061 g_size=519,729,388,118,890 network-upload-bytes=2,622,560,245 network-download-bytes=7,031,151,906 sec=4808.44`)

## Dataverse

Using their restful API `search` (https://guides.dataverse.org/en/latest/api/search.html)
Each requests returns 1000 records (seems a reasonable number, not sure if we can get better results with different page size).
I am doing the search on all public dataverse 58  instances (see `dataverse.py` file for the instances list):

Statistics
- num-datasets=150,834  (using dataset_id)
- num-records=2,596,905
- tot-size=125,441,273,690,687 (125TB)
- network-upload-bytes=2,742,687,197 (2GB)
- network-download-bytes=25,975,441,077 (25GB)
- total-seconds=18313 (5.08 hours)

## Digital Rock Portal

I didn't find an API to do the scraping (I am not sure 100% it does not exists) 
so I am basically scraping HTML pages from https://www.digitalrocksportal.org and parting them with Python bs4 package

Statistics
- num-datasets=154 
- num-records=139,393
- tot-size=8,953,576,105,178 (9TB)
- network-upload-bytes= 25,539,253 (25MB)
- network-download-bytes=114,333,049  (114MB)
- total-seconds=3080 (51 minutes)

## Material Commons

Using using `materials_commons.api` (https://github.com/materials-commons/materialscommons.org)

Statistics:
- num-datasets= 81 
- num-records=131,091
- tot-size=5,750,975,594,582 (5TB)
- network-upload-bytes= 10,951,017 (10MB)
- network-download-bytes=78,353,195 (78MB)
- total-seconds=76


## Globus material data facility

Using `mdf_forge` API (https://github.com/materials-data-facility/forge)

Statistics
- num-datasets=637 
- num-records=1,206,801
- tot-size=10,995,444,243,681 (10TB)
- network-upload-bytes=208,706,961 (208MB)
- network-download-bytes=1,305,295,310 (1GB NOTE: probably I am dowloading extra informations about the projects and there could be a "lighter" API)
- total-seconds=797 (13 minutes)


## Tacc Ranch

It is a simple `find --t f /public/data`. THere is no public repo.

I think internally Ranch uses some sort of catalog to speed up `ls|find` operations, at least for hot data
but I don't have the details.

Statistics
- num-datasets=??? 
- num-records=3,745,761
- tot-size=36,750,124,831,623,293 (36PB)
- network-upload-bytes=n.a.
- network-download-bytes=n.a.
- total-seconds=???

## Zenodo

using zenodopy client (https://github.com/lgloege/zenodopy).
Important to mention:
- each API request cannot return more than 10K items, so I am doing the queries partitioning the time from 20100101 to today() with a delta-days of 5
- with a delta of 5 days we do (2022-2010)*365/5=~876 network requests
- probably using a delta larger we could get better numbers, but I found certain period of 5 days with more than 10K records
- there is a rate limiter of 60 requests per minute and 2000 requests per hour (33 req/min), so I am using an overall 30 calls/min

Rate limiter code:
```
from tkinter import E
from ratelimit import limits, RateLimitException, sleep_and_retry

@sleep_and_retry
@limits(calls=30, period=60) 
def GetJSONResponse(url):
	... code here..
```

Statistics
- num-datasets=1,012,474 (NOTE: using DOI as it was a dataset)
- num-records=3,485,074 (3M)
- tot-size=373,890,709,078,423 (373TB)
- network-upload-bytes=46,367,940 (46MB)
- network-download-bytes=4,238,454,624 (4GB)
- total-seconds=19734 (5.4 hours)


## OpenVisus

It is simple a `find -t f /OpenVisusDirectory`. There is no public repo yet

Statistics
- num-datasets=???
- num-records=~246M files
- tot-size=~124TB
- network-upload-bytes=n.a.
- network-download-bytes=n.a.
- total-seconds=???


