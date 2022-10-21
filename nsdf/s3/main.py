
import os,sys,logging,argparse,time,tempfile,json

from nsdf.kernel import SetupLogger,logger

# ////////////////////////////////////////////////////
def Main(args):
	# see https://github.com/wbingli/awscli-plugin-endpoint
	# python3 -m pip install awscli-plugin-endpoint
	# aws configure set plugins.endpoint awscli_plugin_endpoint
	# aws configure --profile local set dynamodb.endpoint_url http://localhost:8000

	action=args[1]
	action_args=args[2:]
 
	SetupLogger(logger, level=logging.INFO, handlers=[logging.StreamHandler()]) 
 
	# _________________________________________
	if action=="ls":
		# time python3 -m nsdf.s3  ls --only_dirs "s3://Pania_2021Q3_in_situ_data?profile=wasabi&num-connections=48"  > /srv/nvme1/nsdf/pania.json
		# time python3 -m nsdf.s3  ls --only_dirs  "s3://utah?profile=sealstorage&no-verify-ssl&num-connections=48"    > /srv/nvme1/nsdf/sealstorage.json
		
		parser = argparse.ArgumentParser(description=action)
		parser.add_argument('--only-dirs',action='store_true')  
		parser.add_argument('url',type=str)  
		args=parser.parse_args(action_args)
		logger.info(f"Got args {args}")
		
		t1=time.time()
		from nsdf.s3 import S3
		s3=S3(args.url)
		for obj in s3.listObjectsInParallel(args.only_dirs):
			print(json.dumps(obj, default=str))
			sec=time.time()-t1	
			if sec>=2.0: 
				ls.printStatistics()
				t1=time.time()
		return

	if action=="browser":
		"""
		AWS_PROFILE=wasabi NO_VERIFY_SSL=1 python -m nsdf.s3 browser s3://
  
		# for windows under WSL
	  python.exe -m nsdf.s3 browser "s3://?profile=sealstorage&no-verify-ssl=1"
		"""
		from nsdf.s3.browser import Browser
		Browser.run(action_args[0] if action_args else "s3://")
		return 