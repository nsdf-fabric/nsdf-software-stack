
import csv,json,requests,os,sys, threading, time
import concurrent.futures
from pprint import pprint
import yaml
import traceback
import csv

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger('example')

# ////////////////////////////////////////////////////////////////////////
def getDataverseInstances():
	# https://dataverse.org/metrics
	return [
		{"name": "Abacus", "url": "http://abacus.library.ubc.ca"},
		{"name": "ACSS Dataverse", "url": "http://dataverse.theacss.org"},
		{"name": "Arca Dados", "url": "http://dadosdepesquisa.fiocruz.br"},
		{"name": "ASU Library Research Data Repository", "url": "http://dataverse.asu.edu"},
		{"name": "AUSSDA Dataverse", "url": "http://data.aussda.at"},
		{"name": "Borealis", "url": "http://borealisdata.ca"},
		{"name": "CIFOR", "url": "http://data.cifor.org"},
		{"name": "CIMMYT Research Data", "url": "http://data.cimmyt.org"},
		# {"name": "CIRAD Dataverse", "url": "http://dataverse.cirad.fr"},
		{"name": "CORA. Research Data Repository (RDR)", "url": "http://dataverse.csuc.cat"},
		{"name": "CROSSDA", "url": "http://data.crossda.hr"},
		{"name": "CUHK Research Data Repository", "url": "http://researchdata.cuhk.edu.hk"},
		{"name": "Dartmouth Dataverse", "url": "http://dataverse.dartmouth.edu"},
		{"name": "DaRUS", "url": "http://darus.uni-stuttgart.de"},
		# {"name": "Data INRAe", "url": "http://data.inrae.fr"},
		{"name": "Data Suds", "url": "http://dataverse.ird.fr"},
		{"name": "data.sciencespo", "url": "http://data.sciencespo.fr"},
		{"name": "Dataverse e-cienciaDatos", "url": "http://edatos.consorciomadrono.es"},
		{"name": "DataverseNL", "url": "http://dataverse.nl"},
		{"name": "DataverseNO", "url": "http://dataverse.no"},
		{"name": "DR-NTU (Data)", "url": "http://researchdata.ntu.edu.sg"},
		{"name": "Florida International University Research Data Portal", "url": "http://dataverse.fiu.edu"},
		# {"name": "George Mason University Dataverse", "url": "http://dataverse.orc.gmu.edu"},
		{"name": "Göttingen Research Online", "url": "http://data.goettingen-research-online.de"},
		{"name": "Harvard Dataverse", "url": "http://dataverse.harvard.edu"},
		{"name": "HeiDATA", "url": "http://heidata.uni-heidelberg.de"},
		{"name": "IBICT", "url": "http://repositoriopesquisas.ibict.br"},
		{"name": "ICRISAT", "url": "http://dataverse.icrisat.org"},
		{"name": "IFDC Dataverse", "url": "http://dataverse.ifdc.org"},
		{"name": "Ifsttar Dataverse", "url": "http://research-data.ifsttar.fr"},
		{"name": "IISH Dataverse", "url": "http://datasets.iisg.amsterdam"},
		{"name": "Institute of Russian Literature Dataverse", "url": "http://dataverse.pushdom.ru"},
		{"name": "International Potato Center", "url": "http://data.cipotato.org"},
		{"name": "Italian Institute of Technology (IIT)", "url": "http://dataverse.iit.it"},
		{"name": "Johns Hopkins University", "url": "http://archive.data.jhu.edu"},
		{"name": "Jülich DATA", "url": "http://data.fz-juelich.de"},
		{"name": "Libra Data", "url": "http://dataverse.lib.virginia.edu"},
		{"name": "LIPI Dataverse", "url": "http://data.lipi.go.id"},
		{"name": "Lithuanian Data Archive for Social Sciences and Humanities (LiDA)", "url": "http://lida.dataverse.lt"},
		{"name": "MELDATA", "url": "http://data.mel.cgiar.org"},
		{"name": "NIE Data Repository", "url": "http://researchdata.nie.edu.sg"},
		{"name": "NIOZ Dataverse", "url": "http://dataverse.nioz.nl"},
		{"name": "Open Data @ UCLouvain", "url": "http://dataverse.uclouvain.be"},
		{"name": "Open Forest Data", "url": "http://dataverse.openforestdata.pl"},
		{"name": "Peking University", "url": "http://opendata.pku.edu.cn"},
		{"name": "Pontificia Universidad Católica del Perú", "url": "http://datos.pucp.edu.pe"},
		{"name": "QDR Main Collection", "url": "http://data.qdr.syr.edu"},
		{"name": "Repositorio de datos de investigación de la Universidad de Chile", "url": "http://datos.uchile.cl"},
		{"name": "Repositorio de Datos de Investigación Universidad del Rosario", "url": "http://research-data.urosario.edu.co"},
		{"name": "Repositórios Piloto da Rede Nacional de Ensino e Pesquisa", "url": "http://dadosabertos.rnp.br"},
		{"name": "RSU Dataverse", "url": "http://dataverse.rsu.lv"},
		{"name": "Texas Data Repository Dataverse", "url": "http://dataverse.tdl.org"},
		{"name": "UCLA Dataverse", "url": "http://dataverse.ucla.edu"},
		{"name": "UNB Libraries Dataverse", "url": "http://dataverse.lib.unb.ca"},
		{"name": "UNC Dataverse", "url": "http://dataverse.unc.edu"},
		{"name": "University of Manitoba Dataverse", "url": "http://dataverse.lib.umanitoba.ca"},
		{"name": "Università degli Studi di Milano", "url": "http://dataverse.unimi.it"},
		{"name": "UWI", "url": "http://dataverse.sta.uwi.edu"},
		{"name": "VTTI", "url": "http://dataverse.vtti.vt.edu"},
		{"name": "World Agroforestry - Research Data Repository", "url": "http://data.worldagroforestry.org"},
		{"name": "Yale-NUS Dataverse", "url": "http://dataverse.yale-nus.edu.sg"},
	]


# //////////////////////////////////////////////////////////////////////
def GetJSONResponse(query_url):

	response=requests.get(query_url,allow_redirects =True, timeout=(30, 600), verify=False)
	if response.status_code!=200:
		error_msg=f"GetJSONResponse {query_url} response.status_code={response.status_code} not valid {response.reason}"
		logger.info(error_msg)
		raise Exception(error_msg)
	
	ret=json.loads(response.text)

	# check the status
	status=ret.get('status','') 
	if status!='OK':
		error_msg=f"GetJSONResponse {query_url} status={status} not valid"
		logger.info(error_msg)
		raise Exception(error_msg)

	return ret['data']

# //////////////////////////////////////////////////////////////////////
def GetNumberOfFiles(base_url):
	try:
		data=GetJSONResponse(f"{base_url}/api/search?q=*&type=file&start=0&per_page=1")
		ret=int(data['total_count'])
		logger.info(f"GetNumberOfFiles({base_url})={ret}")
		return (ret,"")
	except Exception as ex:
		logger.info(f"ERROR GetNumberOfFiles({base_url}) exception {ex}")
		return (0,str(ex))


# //////////////////////////////////////////////////////////////////////
def GetFiles(base_url, start, per_page=1000):
	logger.info(f"GetFiles {base_url} {start} running...")

	try:
		files=GetJSONResponse(f"{base_url}/api/search?q=*&type=file&start={start}&per_page={per_page}&show_entity_ids=true")["items"]
	except Exception as ex:
		logger.info(f"ERROR in GetFiles {ex}")
		return []

	ret=[]
	for file in files:
		try:
			ret.append((
				base_url, # catalog
				file["dataset_id"] if "dataset_id" in file else 0,  # bucket
				file["name"],  #filename
				file["size_in_bytes"], #size
				file["published_at"],  # last-modification
				file["md5"] if "md5" in file else 0
				))
		except Exception as ex:
			logger.info(f"ERROR GetFiles wrong recond {ex}")

	logger.info(f"GetFiles {base_url} {start} DONE")
	return ret



# //////////////////////////////////////////////////////////////////////
def ProduceYaml(output_filename, instances, max_workers=64):

	"""
	this function scrape all the following DataVerse instances and create a Yaml 'dataverse.yaml' file with the total number of files
	if case of error, the yaml file contains an error message explaining what went wrong
	"""

	with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
		results = executor.map(GetNumberOfFiles, [it["url"] for it in instances])
		
	for I,result in enumerate(results):
		total,error_msg=result
		url=instances[I]["url"]
		instances[I]["total"]=total
		if error_msg:
			instances[I]["error_msg"]=error_msg
		else:
			instances[I].pop("error_msg", None)
		logger.info(f"{url:48} {total:8d} {error_msg}")

	with open(output_filename, 'w') as file:
		yaml.dump(instances, file)


# //////////////////////////////////////////////////////////////////////
def GetAllFiles(instances, output_filename, max_workers=32, per_page=1000):

	"""
	produce a CSV file with all files from all dataverse instances
	NOTE: I split the total-file range in several chunked request
	      for now I do not worry too much of errors and I just ignore them
	"""
	
	f=open(output_filename,"w")
	writer=csv.writer(f)

	with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

		TOTAL,DONE,SIZE=0,0,0
		futures=[]
		for I, it in enumerate(instances):
			base_url,total=it["url"],int(it["total"])
			TOTAL+=total
			for start in range(0, total, per_page):
				futures.append(executor.submit(GetFiles,base_url,start, per_page))

		logger.info(f"Total number of futures={len(futures)} TOTAL={TOTAL} per_page={per_page}")

		for future in concurrent.futures.as_completed(futures):
			files=future.result()
			DONE+=len(files)
			SIZE+=sum([it[3] for it in files])
			logger.info(f"done {DONE}/{TOTAL} {SIZE//1024**3}GB")
			writer.writerows(files)
			f.flush()
	
	f.close()
	


# //////////////////////////////////////////////////////////////////////////////////
def Main():

	"""
	To run:

	python3 nsdf/catalog/dataverse produce-yaml
	python3 nsdf/catalog/dataverse produce-csv

	# copy into the bucket so that you can insert the records in clickhouse
	# (uncomment the following lines to enable the profile...)
	#   cp ~/.nsdf/vault/aws_config ~/.aws/config
	#   cp ~/.nsdf/vault/aws_credentials ~/.aws/credentials
	aws s3 cp --profile cloudbank --endpoint-url https://s3.us-west-1.amazonaws.com dataverse.csv s3://nsdf-catalog/dataverse/
	"""

	action=sys.argv[1]

	if action=="produce-yaml":
		ProduceYaml('dataverse.yaml', getDataverseInstances())

	elif action=="produce-csv":
		with open('dataverse.yaml') as f:
			instances = yaml.load(f, Loader=yaml.FullLoader)
		GetAllFiles(instances, "dataverse.csv")

# //////////////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	Main()


