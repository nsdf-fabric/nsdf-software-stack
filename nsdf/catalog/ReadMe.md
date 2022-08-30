
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

## Ubuntu

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

## Redhat 8

```

sudo yum install -y clickhouse-server clickhouse-client


```
change all 900X ports to 1000X port to avoid conflicts wiht python

```
sudo /etc/init.d/clickhouse-server start
set <listen_host>::</listen_host> (dangerous!)
```

Check connectivity:


```
sudo netstat -antp|grep LIST|grep clickhouse
sudo vi /etc/clickhouse-server/config.xml
sudo /etc/init.d/clickhouse-server restart
sudo tail -n 100  /var/log/clickhouse-server/clickhouse-server.log
sudo netstat -antp|grep LIST|grep clickhouse
# tcp6       0      0 :::10004                :::*                    LISTEN      2198639/clickhouse- 
# tcp6       0      0 :::10005                :::*                    LISTEN      2198639/clickhouse- 
# tcp6       0      0 :::10006                :::*                    LISTEN      2198639/clickhouse- 
# tcp6       0      0 :::10009                :::*                    LISTEN      2198639/clickhouse- 
# tcp6       0      0 :::8123                 :::*                    LISTEN      2198639/clickhouse-

clickhouse-client --host nsdf01 --port 10004
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
IDENTIFIED WITH plaintext_password BY 'XXXXXXXX' 
HOST ANY; 

SHOW USERS;

# WITH GRANT OPTION clauses means that the user we grant the permission to, in turn has access to grant the same permission to other users
GRANT ALL PRIVILEGES ON nsdf.* TO dbuser 
WITH GRANT OPTION; 

SHOW GRANTS FOR dbuser;
```

# Create ClickHouse DB

From bash

```
# credentials needed to download CSV files from S3 (replace name as needed)
eval $(python3 -m nsdf export-env s3-wasabi)

# credentials needed to connect to clickhouse server (replace name as needed)
eval $(python3 -m nsdf export-env clickhouse-nsdf01)

# use client
alias cc="${CLICKHOUSE_CLIENT}"

# use client with query
alias ccq="${CLICKHOUSE_CLIENT} --query"

# count records
alias ccc="ccq 'select count(*) from nsdf.catalog'"


```

Execute the following scripts to populate the db

```
CREATE DATABASE IF NOT EXISTS nsdf;

DROP TABLE IF EXISTS nsdf.catalog;

CREATE TABLE IF NOT EXISTS nsdf.catalog(

   # unique id for object (in clickhouse I don't have autoinrement and this is the only way to have a distributed unique id)
   uuid            UInt64   DEFAULT sipHash64(array(catalog,bucket,name)),

   # https://github.com/ClickHouse/ClickHouse/issues/14634 (3 stands for 10^-3==milliseconds)
   inserted_at     DateTime64(3) DEFAULT now64(), 

   catalog	       LowCardinality(String),
   bucket	       String,
   name            String,
   size            BIGINT,
   last_modified   String NULL, # todo, I need a real date here
   etag            String NULL
) 
ENGINE = MergeTree() 
ORDER BY (catalog, bucket, name)
PRIMARY KEY(catalog, bucket, name) 
SETTINGS index_granularity = 8192;

# NOTE: Not using minmax secondary index anymore, lot better to use projections !!!
# (DEPRECATED) ALTER TABLE nsdf.catalog  
# (DEPRECATED)   ADD INDEX IF NOT EXISTS catalog_pagination (inserted_at, uuid) TYPE minmax GRANULARITY 1;

# using projections instead
# https://www.tinybird.co/blog-posts/projections
SET allow_experimental_projection_optimization = 1;
ALTER TABLE nsdf.catalog ADD PROJECTION projection_paginate(SELECT * ORDER BY uuid);
ALTER TABLE nsdf.catalog MATERIALIZE PROJECTION projection_paginate;

SHOW CREATE TABLE nsdf.catalog;

# if you need to insert faulty records
# set input_format_allow_errors_num=999999;
```

From bash:


```


function InsertRecords {
   pattern=$1
   NUM_RECORDS_BEFORE=$(ccc)
   echo "Doing pattern=${pattern} num-records=${NUM_RECORDS_BEFORE}..."
   CMD=$(cat << EOF
      INSERT INTO nsdf.catalog(catalog, bucket, name, size, last_modified, etag)
      SELECT catalog, bucket, name, size, last_modified, etag
      FROM s3(
         '${pattern}',
         '${AWS_ACCESS_KEY_ID}', 
         '${AWS_SECRET_ACCESS_KEY}', 
         'CSV', 
         'catalog String,bucket String,name String,size String,last_modified String,etag String'
    );
EOF
   )
   cc --input_format_allow_errors_num 999999999 --query "${CMD}"
   NUM_RECORDS_AFTER=$(ccc)
   echo "Done num-records=${NUM_RECORDS_AFTER} delta=$(( NUM_RECORDS_AFTER - NUM_RECORDS_BEFORE ))"
}


ccq "TRUNCATE TABLE nsdf.catalog" && ccc

for catalog in arecibo aws-open-data dataverse digitalrocksportal mc mdf ranch zenodo; do
   InsertRecords "https://s3.us-west-1.wasabisys.com/nsdf-catalog/${catalog}/*.csv"
done

InsertRecords "https://s3.us-west-1.wasabisys.com/nsdf-catalog/aws-open-data/*.csv"

```
  

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



# ClickHouse miscellanous


```
# ClickHouse uses the sorting key as a primary key if the primary key is not defined explicitly by the PRIMARY KEY clause.
show create table nsdf.catalog;
```

Specs:
- vCPU 8
- RAM 32 GB
- SSD Storage 256 GB

```
clickhouse-client --host XXXXX --port 9440 --secure --user admin --password XXXXX
```

# Show Statistics

Links:
- https://gist.github.com/sanchezzzhak/511fd140e8809857f8f1d84ddb937015

```
select
    parts.*,
    columns.compressed_size,
    columns.uncompressed_size,
    columns.ratio
from (
    select database,
        table,
        formatReadableSize(sum(data_uncompressed_bytes))          AS uncompressed_size,
        formatReadableSize(sum(data_compressed_bytes))            AS compressed_size,
        sum(data_compressed_bytes) / sum(data_uncompressed_bytes) AS ratio
    from system.columns
    group by database, table
) columns right join (
    select database,
           table,
           sum(rows)                                            as rows,
           max(modification_time)                               as latest_modification,
           formatReadableSize(sum(bytes))                       as disk_size,
           formatReadableSize(sum(primary_key_bytes_in_memory)) as primary_keys_size,
           any(engine)                                          as engine,
           sum(bytes)                                           as bytes_size
    from system.parts
    where active
    group by database, table
) parts on ( columns.database = parts.database and columns.table = parts.table )
order by parts.bytes_size desc;


┌─parts.database─┬─parts.table──────┬───────rows─┬─latest_modification─┬─disk_size──┬─primary_keys_size─┬─engine──────────────┬──bytes_size─┬─compressed_size─┬─uncompressed_size─┬───────────────ratio─┐
│ nsdf           │ catalog          │ 1549840430 │ 2022-08-27 12:16:38 │ 70.38 GiB  │ 95.60 MiB         │ MergeTree           │ 75570042161 │ 70.26 GiB       │ 258.34 GiB        │ 0.27195532633240216 │
│ system         │ trace_log        │    1360326 │ 2022-08-28 07:11:55 │ 26.68 MiB  │ 1.03 KiB          │ MergeTree           │    27979212 │ 26.24 MiB       │ 379.32 MiB        │  0.0691641303723058 │
│ system         │ metric_log       │      85431 │ 2022-08-28 07:11:58 │ 12.23 MiB  │ 186.00 B          │ MergeTree           │    12823590 │ 11.83 MiB       │ 210.10 MiB        │  0.0562845864464148 │
│ system         │ query_thread_log │      32545 │ 2022-08-28 07:11:39 │ 2.88 MiB   │ 90.00 B           │ MergeTree           │     3022657 │ 2.37 MiB        │ 21.47 MiB         │ 0.11059508795837078 │
│ system         │ query_log        │       7097 │ 2022-08-28 07:11:39 │ 1.05 MiB   │ 66.00 B           │ MergeTree           │     1098120 │ 0.00 B          │ 0.00 B            │                 nan │
│ system         │ part_log         │      17828 │ 2022-08-28 07:11:48 │ 704.96 KiB │ 90.00 B           │ MergeTree           │      721879 │ 0.00 B          │ 0.00 B            │                 nan │
│ system         │ session_log      │      20850 │ 2022-08-28 07:11:48 │ 563.94 KiB │ 90.00 B           │ MergeTree           │      577478 │ 0.00 B          │ 0.00 B            │                 nan │
│ _system        │ write_sli_part   │       1614 │ 2022-08-28 07:12:00 │ 14.02 KiB  │ 24.00 B           │ ReplicatedMergeTree │       14358 │ 0.00 B          │ 0.00 B            │                 nan │
│ _system        │ read_sli_part    │          1 │ 2022-08-27 07:28:02 │ 84.00 B    │ 22.00 B           │ ReplicatedMergeTree │          84 │ 0.00 B          │ 0.00 B            │                 nan │
└────────────────┴──────────────────┴────────────┴─────────────────────┴────────────┴───────────────────┴─────────────────────┴─────────────┴─────────────────┴───────────────────┴─────────────────────┘
```

# Export catalog

Links:
- https://www.clairvoyant.ai/blog/big-data-file-formats

```
https://groups.google.com/g/clickhouse/c/noXKVLtv3hw
SET max_threads=1;
SET max_memory_usage=50000000000;


# 1549840430 rows in set. Elapsed: 1423.112 sec (23 minutes). Processed 1.55 billion rows, 339.19 GB (1.09 million rows/s., 238.34 MB/s.)
# file size on disk 76GB
# aws s3 --profile wasabi cp /srv/nvme1/nsdf/catalog.pq s3://nsdf-catalog/click-house/ && rm -f /srv/nvme1/nsdf/catalog.pq
SELECT * FROM nsdf.catalog INTO OUTFILE '/srv/nvme1/nsdf/catalog.pq'    FORMAT Parquet; 

# fails, it's creating a file >255GB (!!!) that's is my SSD size (it seems like it writes the data UNCOMPRESSED)
SELECT * FROM nsdf.catalog INTO OUTFILE '/srv/nvme0/nsdf/catalog.arrow' FORMAT Arrow;

# 1549840430 rows in set. Elapsed: 1337.043 sec. Processed 1.55 billion rows, 339.19 GB (1.16 million rows/s., 253.69 MB/s.)
# file size on disk 242G
# aws s3 --profile wasabi cp /srv/nvme0/nsdf/catalog.orc s3://nsdf-catalog/click-house/ && rm -f /srv/nvme0/nsdf/catalog.orc
SELECT * FROM nsdf.catalog INTO OUTFILE '/srv/nvme0/nsdf/catalog.orc'   FORMAT ORC;  
```

# Benchmarks without UUID (problem with paging)

Links:
- https://www.eversql.com/faster-pagination-in-mysql-why-order-by-with-limit-and-offset-is-slow/
- https://groups.google.com/g/clickhouse/c/WAbb4i3SpqM
- https://stackoverflow.com/questions/60655850/why-adding-offset-to-the-clickhouse-query-increase-execution-time
- https://use-the-index-luke.com/no-offset
- https://super-unix.com/database/postgresql-how-to-do-pagination-with-uuid-v4-and-created-time-on-concurrent-inserted-data/
- SOLUTION (!) https://www.tinybird.co/blog-posts/projections

```
# 100 rows in set. Elapsed: 1.107 sec.
select * from nsdf.catalog                            LIMIT 100 OFFSET 0; 

# 100 rows in set. Elapsed: 1.134 sec. Processed 65.54 thousand rows, 24.63 MB (57.80 thousand rows/s., 21.73 MB/s.)
select * from nsdf.catalog ORDER BY  catalog, bucket  LIMIT 100 OFFSET 0; 

# 100 rows in set. Elapsed: 236.384 sec. Processed 1.55 billion rows, 339.19 GB (6.56 million rows/s., 1.43 GB/s.)
select * from nsdf.catalog ORDER BY (catalog, bucket) LIMIT 100 OFFSET 0; 

# 100 rows in set. Elapsed: 244.153 sec. Processed 1.50 billion rows, 329.11 GB (6.14 million rows/s., 1.35 GB/s.)
select * from nsdf.catalog                            LIMIT 100 OFFSET 1500000000; 

# 100 rows in set. Elapsed: 901.500 sec. Processed 1.50 billion rows, 327.72 GB (1.66 million rows/s., 363.52 MB/s.)
select * from nsdf.catalog ORDER BY  catalog, bucket  LIMIT 100 OFFSET 1500000000; 

# DB::Exception: Memory limit (for query) exceeded: would use 9.32 GiB
select * from nsdf.catalog ORDER BY  catalog, bucket  LIMIT 100 OFFSET 1500000000  SETTINGS optimize_read_in_order=0;

#  DB::Exception: Memory limit (for query) exceeded: would use 9.32 GiB
select * from nsdf.catalog ORDER BY (catalog, bucket) LIMIT 100 OFFSET 1500000000; 
```

# Catalog with UUID


Links:
- https://clickhouse.com/docs/en/guides/improving-query-performance/sparse-primary-indexes/sparse-primary-indexes-uuids/
- https://www.alibabacloud.com/blog/secondary-index-in-alibaba-cloud-clickhouse-best-practices_597894

Notes:
- IMPORTANT that we have low cardinality on the left of order by, primary key to have better compressions

```
# ALTER TABLE    nsdf.catalog ADD COLUMN uuid UUID DEFAULT generateUUIDv4() FIRST;
# ALTER TABLE    nsdf.catalog ADD INDEX  uuid_index uuid TYPE minmax GRANULARITY 32;
# OPTIMIZE TABLE nsdf.catalog FINAL;

DROP TABLE IF EXISTS nsdf.catalog_uuid;

CREATE TABLE nsdf.catalog_uuid(
    uuid                   UUID,
    catalog                String,
    bucket                 String,
    name                   String,
    size                   Int64,
    last_modified Nullable(String),
    etag          Nullable(String),

    # https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/mergetree/#available-types-of-indices
    # minmax, set, ngrambf_v1, tokenbf_v1 or bloom_filter
    INDEX uuid_index uuid TYPE minmax GRANULARITY 32
)
ENGINE = MergeTree  
ORDER BY (catalog, bucket, name, uuid)  
PRIMARY KEY(catalog, bucket, name, uuid) 
SETTINGS index_granularity = 8192;

SHOW CREATE TABLE nsdf.catalog_uuid;

# max memory, min number of threads
SET max_threads=1;

SET max_memory_usage=50000000000;

INSERT INTO nsdf.catalog_uuid 
SELECT generateUUIDv4(),catalog,bucket,name,size,last_modified,etag 
FROM nsdf.catalog;
```

# Benchmarks with UUID

```
select * from nsdf.catalog ORDER BY uuid  LIMIT 100 OFFSET 0; 
select * from nsdf.catalog ORDER BY uuid  LIMIT 100 OFFSET 1500000000; 
select * from nsdf.catalog ORDER BY uuid  LIMIT 100 OFFSET 1500000000  SETTINGS optimize_read_in_order=0;


```



