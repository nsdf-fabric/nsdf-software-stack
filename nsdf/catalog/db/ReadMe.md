# Preliminary steps


Create an `.env` file with the content (change as needed):

```
AWS_ACCESS_KEY_ID=XXXXX
AWS_SECRET_ACCESS_KEY=YYYYY
CLICKHOUSE_HOST=ZZZZ
CLICKHOUSE_PORT=9440
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=KKKKK 
CLICKHOUSE_SECURE=True
```

Export `.env` variables to the current terminal:

```
set -o allexport
source ".env"
set +o allexport

# test aws credentials
aws s3 --profile wasabi ls s3://

# test clickhouse
alias cc="clickhouse-client --receive_timeout 9999999 --host ${CLICKHOUSE_HOST} --port ${CLICKHOUSE_PORT} --secure --user ${CLICKHOUSE_USER} --password ${CLICKHOUSE_PASSWORD}"

cc
```


# Create database

Create the database:

```
cc

DROP DATABASE IF EXISTS nsdf;

CREATE DATABASE IF NOT EXISTS nsdf;

# https://github.com/ClickHouse/ClickHouse/issues/14634 (3 stands for 10^-3==milliseconds)
CREATE TABLE IF NOT EXISTS nsdf.catalog(

   catalog	       LowCardinality(String),
   bucket	       String,
   name            String,
   size            BIGINT,
   last_modified   String NULL, 
   etag            String NULL,
   inserted_at     DateTime64(3) DEFAULT now64(),

	# max 6 chars allowed
   ext             LowCardinality(String) MATERIALIZED IF( length(splitByChar('.',name)[-1])<=6 , splitByChar('.',name)[-1] , '') 
) 
ENGINE = MergeTree() 
ORDER BY (catalog, bucket, name)
PRIMARY KEY(catalog, bucket, name) 
SETTINGS index_granularity = 8192;



# *** materialized view I believe could help us to speed up some queries (Need to ask Adam feedback on this) ***
# *** NOTE: seems to me that this view is slowing A LOT the INSERT process                                   ***

DROP view nsdf.aggregated_catalog;

CREATE MATERIALIZED VIEW nsdf.aggregated_catalog 
ENGINE = SummingMergeTree
PARTITION BY (catalog)
ORDER BY (catalog, bucket, ext)
POPULATE AS
SELECT catalog, bucket, ext, SUM(size) as tot_size, COUNT(size) as num_files
FROM nsdf.catalog
GROUP BY catalog, bucket, ext
ORDER BY catalog, bucket, ext, tot_size DESC, num_files DESC;

# SELECT * from nsdf.aggregated_catalog;

exit
```

From bash:

```
# remove all records
# cc --query "TRUNCATE TABLE nsdf.catalog" 

# show number of records
# cc --query 'select count(*) from nsdf.catalog'

# list all files to insert
FILES=$(aws s3 --profile wasabi ls --recursive s3://nsdf-catalog/ | grep ".csv.gz" | awk '{print "https://s3.us-west-1.wasabisys.com/nsdf-catalog/" $4}')

DIRS=$(echo $FILES | xargs dirname | sort -u)

# /////////////////////////////////////////////////////////////////////
# insert records

for dir in ${DIRS}; do
   echo "Doing ${dir}..."
   QUERY=$(cat <<EOF
      INSERT INTO nsdf.catalog(catalog, bucket, name, size, last_modified, etag)
      SELECT catalog, bucket, name, size, last_modified, etag
      FROM s3(
         '${dir}/*.csv.gz',
         '${AWS_ACCESS_KEY_ID}', 
         '${AWS_SECRET_ACCESS_KEY}', 
         'CSV', 
         'catalog String, bucket String, name String, size String, last_modified String, etag String'
      );
EOF
	)
   cc --input_format_allow_errors_num 999999999 -max_threads=16 --max_insert_threads=16  --query "${QUERY}"
done

# overall statistivs (1,590,981,170 == 1.5 billion) (84,795,345,554,398,043 == 84 PiB)
cc --query 'select count(name), SUM(size)from nsdf.catalog'
cc --query 'select SUM(num_files), SUM(tot_size)from nsdf.aggregated_catalog'

# total number of catalogs (53 catalogs)
# cc --query 'SELECT DISTINCT catalog FROM nsdf.aggregated_catalog' 
```
  

# (OPTIONAL) Show partition statistics

Links:

- https://gist.github.com/sanchezzzhak/511fd140e8809857f8f1d84ddb937015
- **NSDF-catalog it's a 257GiB database uncompressed, 72GiB compressed (primary key it's 117MiB)**

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
```

## (OPTIONAL) Export database

Links:
- https://www.clairvoyant.ai/blog/big-data-file-formats
- https://groups.google.com/g/clickhouse/c/noXKVLtv3hw

```
SET max_threads=1;
SET max_memory_usage=50000000000;
SELECT * FROM nsdf.catalog INTO OUTFILE '/srv/nvme1/nsdf/catalog.pq'    FORMAT Parquet; 
SELECT * FROM nsdf.catalog INTO OUTFILE '/srv/nvme0/nsdf/catalog.arrow' FORMAT Arrow;
SELECT * FROM nsdf.catalog INTO OUTFILE '/srv/nvme0/nsdf/catalog.orc'   FORMAT ORC;  
```

## (OPTIONAL)Paging problem 

Links:
- https://www.eversql.com/faster-pagination-in-mysql-why-order-by-with-limit-and-offset-is-slow/
- https://groups.google.com/g/clickhouse/c/WAbb4i3SpqM
- https://stackoverflow.com/questions/60655850/why-adding-offset-to-the-clickhouse-query-increase-execution-time
- https://use-the-index-luke.com/no-offset
- https://super-unix.com/database/postgresql-how-to-do-pagination-with-uuid-v4-and-created-time-on-concurrent-inserted-data/
- https://clickhouse.com/docs/en/guides/improving-query-performance/sparse-primary-indexes/sparse-primary-indexes-uuids/
- https://www.alibabacloud.com/blog/secondary-index-in-alibaba-cloud-clickhouse-best-practices_597894
- https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/mergetree/#available-types-of-indices
- https://www.tinybird.co/blog-posts/projections (MAYBE the solution?)

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

With UUID column/index:

```
ALTER TABLE    nsdf.catalog ADD COLUMN uuid UUID DEFAULT generateUUIDv4() FIRST;
ALTER TABLE    nsdf.catalog ADD INDEX  uuid_index uuid TYPE minmax GRANULARITY 32;
OPTIMIZE TABLE nsdf.catalog FINAL;


select * from nsdf.catalog ORDER BY uuid  LIMIT 100 OFFSET 0; 
select * from nsdf.catalog ORDER BY uuid  LIMIT 100 OFFSET 1500000000; 
select * from nsdf.catalog ORDER BY uuid  LIMIT 100 OFFSET 1500000000  SETTINGS optimize_read_in_order=0;
```


# (OPTIONAL) Install ClickHouse on Ubuntu

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

# (OPTIONAL) Install ClickHouse on RedHat 8

```
sudo yum install -y clickhouse-server clickhouse-client
```

Change all 900X ports to 1000X port to avoid conflicts wiht python:

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

# (OPTIONAL) Check ClickHouse onnectivity

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

# (OPTIONAL) Add ClickHouse dbuser

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
