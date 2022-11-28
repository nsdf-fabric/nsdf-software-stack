"""
Using using `materials_commons.api` (https://github.com/materials-commons/materialscommons.org)

Statistics:
- num-datasets= 81 
- num-records=131,091
- tot-size=5,750,975,594,582 (5TB)
- network-upload-bytes= 10,951,017 (10MB)
- network-download-bytes=78,353,195 (78MB)
- total-seconds=76
"""

import materials_commons.api as mcapi

import os

from nsdf.kernel import HumanSize, logger

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

	# listCatalogObjects
	def listCatalogObjects(self,args):
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
		logger.info(f"MaterialCommonsCatalog::listCatalogObjects END dataset_id({dataset_id}) #({COUNT}) size({HumanSize(BYTES)})")
		return ret


