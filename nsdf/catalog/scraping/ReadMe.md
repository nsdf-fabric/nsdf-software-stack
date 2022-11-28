
# Instructions


Links:
- [NYC Click Tutorial](https://tech.marksblogg.com/billion-nyc-taxi-rides-clickhouse-cluster.html)


# Scraping

## Setup the DASK cluster

Install python wheels:

```
PACKAGES="materials-commons-api mysql-connector-python mdf_forge boto3 awscli imageio clickhouse-driver prefect bs4 pandas"

# if running on local host
python3 -m pip install $PACKAGES

# if running on DASK do instead 
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

## (OPTIONAL) mount SSD disk

```
lsblk
sudo mkfs -t ext4 /dev/nvme1n1
sudo mkdir /vol_b
sudo mount /dev/nvme1n1 /vol_b
df -h
sudo chown -R ubuntu /vol_b
sudo chmod a+rwX /vol_b
```


## Performance

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
