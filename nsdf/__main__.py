import os,sys,time

from nsdf.kernel import ListObjects,S3,SetupLogger,logger


# ////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
    
	action=sys.argv[1]
 
	# _________________________________________
	if action=="export-env":
		"""
		python3 -m nsdf export-env s3-wasabi
		"""
		account=sys.argv[sys.argv.index( "export-env")+1]
		from nsdf.kernel import NormalizeEnv, PrintEnv, SetEnv, LoadVault
		vault=LoadVault()
		env=NormalizeEnv(vault[account]["env"])
		PrintEnv(env)
		sys.exit(0)
	
  	# _________________________________________
	if action=="lines-per-sec":
		N,T1,t1 = 0,time.time(),time.time()
		for line in sys.stdin:
			N+=1
			now=time.time()
			if (now-t1)>2.0:
				t1=now
				sec = now - T1
				print(f"Elapsed time={sec} lines={N:,} lps={N//sec}")
		sys.exit(0)
  
	import logging
	SetupLogger(logger, level=logging.INFO, handlers=[logging.StreamHandler()]) 

	# _________________________________________
	if action=="list-objects":
		# python3 -m nsdf  list-objects
		# on JHU with 48 connections I can reach ~10K objects/sec (7 hours for 246M objects)
		nworkers=48
		# redis_server = redis.StrictRedis('localhost',6379, charset="utf-8", decode_responses=True)
		s3=S3(aws_profile="wasabi", endpoint_url="https://s3.us-west-1.wasabisys.com") 
		# s3=S3(aws_profile="sealstorage", endpoint_url="https://maritime.sealstorage.io/api/v0/s3") 
		ls=ListObjects(s3, "s3://Pania_2021Q3_in_situ_data",nworkers)
		time.sleep(3600*24*365)
		sys.exit(0)