import materials_commons.api as mcapi

import os

from nsdf.kernel import StringFileSize, logger

# /////////////////////////////////////////////////////////////////////
class MaterialCommonsCatalog:

	# constructor
	def __init__(self,name):
		self.token=os.environ["MC_TOKEN"]
		self.name=name

	# listDatasets
	def listDatasets(self, args={}):
		client=mcapi.Client(self.token)
		datasets=client.get_all_published_datasets()
		# datasets=[dataset for dataset in datasets if len(client.get_published_dataset_files(dataset.id))>0 ]
		ret=[{
			'dataset_id':dataset.id
			} for dataset in datasets]
		logger.info(f"MaterialCommonsCatalog::listDatasets #({len(ret)})")
		return ret

	# getDatasetKey
	def getDatasetKey(self,args):
		dataset_id=args["dataset_id"]
		return "{}/{}".format(self.name,dataset_id)

	# listObjects
	def listObjects(self,args):
		dataset_id=args["dataset_id"]
		client=mcapi.Client(self.token)
		files = client.get_published_dataset_files(dataset_id)
		ret=[]
		BYTES,COUNT=0,0
		for file in files:
			ret.append([
				self.name,
				dataset_id,
				file.name, 
				file.size, 
				None,
				file.checksum])
			BYTES+=file.size
			COUNT+=1
		logger.info(f"MaterialCommonsCatalog::listObjects END dataset_id({dataset_id}) #({COUNT}) size({StringFileSize(BYTES)})")
		return ret


