
# Instructions


Links:
- [NYC Click Tutorial](https://tech.marksblogg.com/billion-nyc-taxi-rides-clickhouse-cluster.html)


# Setup the cluster

Install python wheels:

```

PACKAGES="materials-commons-api mysql-connector-python mdf_forge"

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
aws s3 --endpoint-url=${AWS_ENDPOINT_URL} mb $(dirname ${REMOTE})
aws s3 --endpoint-url=${AWS_ENDPOINT_URL} ls ${REMOTE}

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

