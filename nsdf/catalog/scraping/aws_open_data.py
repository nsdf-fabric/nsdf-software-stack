"""
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
"""

import os,time

import boto3
import botocore
import botocore.config

import subprocess,glob,yaml

from nsdf.kernel import logger, HumanSize

# //////////////////////////////////////////////////////////////
class AWSOpenDataCatalog:

	# constructor
	def __init__(self, name):
		self.name=name
		
	# listDatasets
	def listDatasets(self,args={}):

		#logger.info(f"AWSOpenDataCatalog::listDatasets BEGIN")

		if not os.path.isdir("/tmp/open-data-registry"):
			subprocess.run(["git","clone","https://github.com/awslabs/open-data-registry.git","/tmp/open-data-registry"], check=True)

		datasets={}
		for filename in glob.glob("/tmp/open-data-registry/datasets/*.yaml"):
			datasets[filename]=yaml.safe_load(open(filename,'r').read())

		ret={}
		for filename in datasets:
			value=datasets[filename]
			for resource in value["Resources"]:
				if resource["Type"]=="S3 Bucket":
					if not "ControlledAccess" in resource:
						bucket_name=resource["ARN"].split(":::")[1]

						# NOTE: in AWS Open Data I can have several item for the same bucket (e.g. bucket/prefix/1/whatever bucket/prefix2/whatever)
						bucket_name=bucket_name.split("/")[0]

						# open bucket is a dictiorary item with name and endpoint_url
						ret[bucket_name]={
							'bucket_name':bucket_name,
							'endpoint_url': "https://s3.{}.amazonaws.com".format(resource["Region"]),
							'aws_filename': filename
						}
						
		ret=list(ret.values())
		logger.info(f"AWSOpenDataCatalog::listDatasets END #({len(ret)})")
		return ret

	# getDatasetKey
	def getDatasetKey(self,args):
		bucket_name=args['bucket_name']
		return "{}/{}".format(self.name,bucket_name)

	# listCatalogObjects
	def listCatalogObjects(self,args):
		bucket_name=args['bucket_name']
		endpoint_url=args['endpoint_url']

		T1=time.time()
		t1=time.time()

		# logger.info("AWSOpenDataCatalog::listCatalogObjects BEGIN bucket_name({bucket_name}) endpoint_url({endpoint_url})")

		# NOTE for some I would need --request-payer requester
		self.s3 = boto3.resource('s3')

		s3 = boto3.client('s3', 
			endpoint_url=endpoint_url, 
			config=botocore.config.Config(signature_version=botocore.UNSIGNED))

		BYTES,COUNT=0,0
		ret=[]
		kwargs = {'Bucket': bucket_name,'MaxKeys':1000}
		while True:

			try:
				resp = s3.list_objects_v2(**kwargs)
			except Exception as e:
				# nothing i can do !
				if "Access Denied" in str(e):
					break 

			if 'Contents' in resp:
				for obj in resp['Contents']:
					size=int(obj['Size'])
					ret.append([
						self.name,
						bucket_name,
						obj['Key'],
						size,
						str(obj["LastModified"]),
						obj['ETag'].strip("\"")
					])
					COUNT+=1
					BYTES+=size

			if (time.time()-t1)>20.0:
				logger.info(f"...(cont.) AWSOpenDataCatalog::listCatalogObjects CONT bucket_name({bucket_name}) endpoint_url({endpoint_url}) #({COUNT}) size({HumanSize(BYTES)}) {int(time.time()-T1)} seconds")
				t1=time.time()

			# try the continuation
			try:
				kwargs['ContinuationToken'] = resp['NextContinuationToken']
			except KeyError:
				break

		logger.info(f"AWSOpenDataCatalog::listCatalogObjects bucket_name({bucket_name}) endpoint_url({endpoint_url}) #({COUNT}) size({HumanSize(BYTES)}) done in {int(time.time()-T1)} seconds")
		return ret


