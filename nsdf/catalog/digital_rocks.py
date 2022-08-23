import requests,time
from   urllib.parse import urlparse

# for HTML parsing
from bs4 import BeautifulSoup

from nsdf.kernel import logger, HumanSize

# ///////////////////////////////////////////////////////////////////////
class DigitalRocksPortalCatalog:

	# constructor
	def __init__(self,name):
		self.name=name
		self.base_url="https://www.digitalrocksportal.org"

	# listDatasets
	def listDatasets(self, args={}):
		ret=[]
		soup = BeautifulSoup(requests.get(self.base_url + "/projects/").content, "html.parser")
		for it in soup.find_all("a",href=True):
			href=it["href"]
			v=href.split("projects/")
			if len(v)==2 and v[0]=="/" and v[1].isdigit():
				ret.append({'project':href})
		return ret

	# getDatasetKey
	def getDatasetKey(self,args):
		project=args["project"]
		return "{}{}".format(self.name,project)

	# __getOriginData
	def __getOriginData(self,project):
		soup = BeautifulSoup(requests.get(self.base_url + project).content, "html.parser")
		ret=[]
		for it in soup.find_all("a",href=True):
			href=it["href"]
			if href.startswith(project + "/origin_data/"):
				ret.append(href)
		return ret

	# __getFiles
	def __getFiles(self,project,origin_data):
		ret=[]
		soup = BeautifulSoup(requests.get(self.base_url + origin_data).content, "html.parser")
		for it in soup.find_all("a",href=True):
			href=it["href"]
			if href.endswith("/download/"):
				# print("HREF",href,"...")
				response=requests.head(self.base_url+ href, allow_redirects=True)
				ret.append([
					self.name, 
					project,
					urlparse(response.url).path,
					int(response.headers.get('Content-Length',0)),
					response.headers.get('Last-Modified',''),
					response.headers.get('ETag','')
				])
				self.COUNT+=1
				self.BYTES+=int(response.headers.get('Content-Length',0))
		return ret

	# listCatalogObjects
	def listCatalogObjects(self,args):
		t1=time.time()
		project=args["project"]
		ret=[]
		self.BYTES=0
		self.COUNT=0
		for origin_data in self.__getOriginData(project):
			ret.extend(self.__getFiles(project,origin_data))
		sec=time.time()-t1
		logger.info(f"DigitalRocksPortalCatalog::listCatalogObjects END project({project}) #({self.COUNT}) size({HumanSize(self.BYTES)}) {sec} seconds")
		return ret

