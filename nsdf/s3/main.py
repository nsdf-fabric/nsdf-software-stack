
import os,sys,logging,argparse,time,tempfile,json

from nsdf.kernel import SetupLogger,logger



# ////////////////////////////////////////////////////
def Main(args):
	# see https://github.com/wbingli/awscli-plugin-endpoint
	# python3 -m pip install awscli-plugin-endpoint
	# aws configure set plugins.endpoint awscli_plugin_endpoint
	# aws configure --profile local set dynamodb.endpoint_url http://localhost:8000

	action=args[1]
 
	SetupLogger(logger, level=logging.INFO, handlers=[logging.StreamHandler()]) 
 
	# _________________________________________
	if action=="ls":
		# time python3 -m nsdf.s3  ls --only_dirs "s3://Pania_2021Q3_in_situ_data?profile=wasabi&num-connections=48"  > /srv/nvme1/nsdf/pania.json
		# time python3 -m nsdf.s3  ls --only_dirs  "s3://utah?profile=sealstorage&no-verify-ssl&num-connections=48"    > /srv/nvme1/nsdf/sealstorage.json
		
		parser = argparse.ArgumentParser(description=action)
		parser.add_argument('--only-dirs',action='store_true')  
		parser.add_argument('url',type=str)  
		args=parser.parse_args(args[2:])
		logger.info(f"Got args {args}")
		
		t1=time.time()
		from nsdf.s3 import ListObjects
		ls=ListObjects(args.url,args.only_dirs)
		for obj in ls:
			print(json.dumps(obj, default=str))
			sec=time.time()-t1	
			if sec>=2.0: 
				ls.printStatistics()
				t1=time.time()
   
		return

	# _________________________________________
	if action=="copy-objects":
     
		"""
  
		sudo yum install -y yum-utils
		sudo yum-config-manager --add-repo https://packages.clickhouse.com/rpm/clickhouse.repo
		sudo yum install -y clickhouse-server clickhouse-client
		sudo clickhouse start

		clickhouse-client

		# do this for pania and sealstorage
		CREATE TABLE IF NOT EXISTS pania(
		    Key varchar(1024),
		    LastModified varchar(32),
		    Etag varchar(16),
		    Size UInt64,
		    StorageClass varchar(16)
		) 
		ENGINE = MergeTree() 
		ORDER BY(Key)
		PRIMARY KEY(Key)
		;
		select count(*) from pania;

		# 246M rows in 2m15.715s
		time cat data/pania.json       | grep Key | clickhouse-client --query="INSERT INTO pania FORMAT JSONEachRow"
  
		#  15M rows in 0m11.774s
		time cat data/sealstorage.json | grep Key | clickhouse-client --query="INSERT INTO sealstorage FORMAT JSONEachRow" 

		# 14.034 sec	
		# Processed 252.22 million rows, 25.63 GB (17.97 million rows/s., 1.83 GB/s.)
		time clickhouse-client --query="SELECT count(*) FROM pania AS src LEFT JOIN (select Key from sealstorage) dst ON dst.Key=CONCAT('{Dprefix}',src.Key) WHERE dst.Key=''"
  		"""
		"""

while [[ 1 == 1 ]] ; do WORKER_ID=0 NUM_WORKERS=1 python3 -m nsdf.s3 copy-objects \
    "s3://Pania_2021Q3_in_situ_data?profile=wasabi&num-connections=128"  \
    "s3://utah/buckets/Pania_2021Q3_in_situ_data?profile=sealstorage&num-connections=128&no-verify-ssl" ; done
		"""
		parser = argparse.ArgumentParser(description=action)
		parser.add_argument('src',type=str)  
		parser.add_argument('dst',type=str) 
		args=parser.parse_args(args[2:])
		logger.info(f"{action} got args {args}")

		tmp_dir="/srv/nvme0/nsdf/tmp"
		# make sure you have enough space 
		os.makedirs(tmp_dir,exist_ok=True)  
		with tempfile.TemporaryDirectory(prefix=tmp_dir) as tmpdirname:
			from nsdf.s3 import CopyObjects
			cp=CopyObjects(args.src,args.dst,tmpdirname)
			for src_row,dst_row,error_msg in cp:
				cp.dst.db.execute('INSERT INTO sealstorage VALUES',[dst_row])
				# print(src_row[0],dst_row[0],error_msg)

		return 
