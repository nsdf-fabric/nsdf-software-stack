import os, sys, base64, glob, subprocess, time, logging, datetime
from   pprint import pprint
from   nsdf.kernel import logger, WriteCSV, HumanSize, SetupLogger, LoadYaml, FileExists,NormalizeEnv, PrintEnv, SetEnv
from   nsdf.s3 import S3

from prefect import task, Flow, unmapped

# AWS Open Data
from nsdf.catalog.aws_open_data import AWSOpenDataCatalog

# Digital Rocks portal
from nsdf.catalog.digital_rocks import DigitalRocksPortalCatalog

# material commons
from nsdf.catalog.material_commons import MaterialCommonsCatalog

# Globus material data faciltit
from nsdf.catalog.material_data_facility import MaterialDataFacility

# ///////////////////////////////////////////////////////////
def ListDatasets(catalog):
	ret=catalog.listDatasets()
	logger.info(f"ListDatasets for catalog {catalog} found {len(ret)} datasets")
	return ret

@task
def ListDatasetsTask(catalog):
	try:
		return ListDatasets(catalog)
	except Exception as ex:
		import traceback
		logger.error(f"ListDatasetsTask ERROR: {traceback.format_exc()}")
		# better to continue anyway?
		# raise 

# ///////////////////////////////////////////////////////////
def ListCatalogObjects(catalog, dataset, loc, rem, dry_run=False, force=False):

	key=catalog.getDatasetKey(dataset)
	loc=loc.format(key=catalog.getDatasetKey(dataset))
	rem=rem.format(key=catalog.getDatasetKey(dataset))

	logger.info(f"ListCatalogObjects catalog={catalog} dataset={dataset} loc={loc} rem={rem}...")
	if dry_run:
		return

	s3=S3(num_connections=1)
	if not force and s3.existObject(rem):
		logger.info(f"{rem} already exists. No need to recreate it")
		return

	t1=time.time()
	objects=catalog.listCatalogObjects(dataset)
	WriteCSV(loc,objects)
	filesize=HumanSize(os.path.getsize(loc))
	logger.info(f"ListCatalogObjectsToCsvTask dataset({dataset}) loc({loc}) rem({rem}) #({len(objects)}) file_size({filesize}) {int(time.time()-t1)} seconds")
	s3.uploadObject(loc, rem)

@task
def ListCatalogObjectsTask(catalog, dataset, loc, rem, dry_run=False):
	try:
		return ListCatalogObjects(catalog, dataset, loc, rem, dry_run=dry_run)
	except Exception as ex:
		import traceback
		logger.info(f"ListCatalogObjectsTask Error: {traceback.format_exc()}")
		# better to continue anyway?
		# raise



# ////////////////////////////////////////////////////////////////////////
if __name__=="__main__":

	workflow=LoadYaml(os.path.join(os.path.dirname(__file__),"workflow.yaml"))

	# enviroment from the workflow
	if True:
		env=NormalizeEnv(workflow["env"])
		if "export-env" in sys.argv:
			PrintEnv(env)
			sys.exit(0)
		SetEnv(env)

	loc=os.environ["LOCAL" ]
	rem=os.environ["REMOTE"]

	# setup logging
	if True:
		log_filename=os.path.join(loc,"logs","nsdf-catalog.log")
		os.makedirs(os.path.dirname(log_filename),exist_ok=True)
		SetupLogger(logger, level=logging.INFO, handlers=[
			logging.StreamHandler(),
			logging.FileHandler(log_filename)])

	# list of catalogs
	catalogs=[]

	catalogs.append(MaterialCommonsCatalog("mc"))
	catalogs.append(DigitalRocksPortalCatalog("digitalrocksportal"))
	catalogs.append(AWSOpenDataCatalog("aws-open-data"))
	catalogs.append(MaterialDataFacility("mdf"))
	

	# _______________________________________________
	def Summarize(num_threads=128):
		from multiprocessing.pool import ThreadPool
		s3=S3(num_connections=num_threads)
		p = ThreadPool(num_threads)
		datasets=p.map(ListDatasets,catalogs)
		ARGS=[]
		for C,catalog in enumerate(catalogs):
			for dataset in datasets[C]:
				ARGS.append([catalog,dataset])
		def Checker(args):
			catalog,dataset=args
			key=catalog.getDatasetKey(dataset)
			return (catalog,dataset,s3.existObject((rem + "/csv/{key}.csv").format(key=key)))
		return p.map(Checker,ARGS)

	summarize="--summarize" in sys.argv
	if summarize:
		for it in Summarize():
			logger.info(f"{it}")
		sys.exit(0)

	# run in parallel on a DASK cluster
	if "dask" in workflow  and bool(workflow["dask"].get("enabled",False)):
		inventory=workflow["dask"]["inventory"]
		group=workflow["dask"]["group"]
		num_process_per_host=int(workflow["dask"]["num-process-per-host"])
		worker_local_dir=workflow["dask"]["worker-local-dir"]

		from nsdf.distributed import NSDFDaskCluster
		cluster = NSDFDaskCluster({
			"inventory": inventory,
			"group": group,
			"num-process-per-host": num_process_per_host,
			"worker-local-dir": worker_local_dir,
			"need-cuda": False,
			"env" : env
		})

		with cluster.connect() as client: 
			tasks=[]
			with Flow("nsdf-catalog") as flow:
				for catalog,dataset,exist in Summarize():
					if exist: continue
					tasks.append(ListCatalogObjectsTask(catalog=catalog, dataset=dataset, 
						loc=loc + "/csv/{key}.csv",
						rem=rem + "/csv/{key}.csv"))

		state=cluster.execute(flow,tasks)
		cluster.close()

	# run serially on local host (useful for debugging)
	else:
		for catalog,dataset,exist in Summarize():
			if exist: continue
			ListCatalogObjects(catalog, dataset, 
				loc + "/csv/{key}.csv", 
				rem + "/csv/{key}.csv")
