
"""
Using their restful API `search` (https://guides.dataverse.org/en/latest/api/search.html)
Each requests returns 1000 records (seems a reasonable number, not sure if we can get better results with different page size).
I am doing the search on all public dataverse 58  instances (see `dataverse.py` file for the instances list):

Statistics
- num-datasets=150,834  (using dataset_id)
- num-records=2,596,905
- tot-size=125,441,273,690,687 (125TB)
- network-upload-bytes=2,742,687,197 (2GB)
- network-download-bytes=25,975,441,077 (25GB)
- total-seconds=18313 (5.08 hours)
"""

import csv,json,requests,os,sys, threading, time
import concurrent.futures
from pprint import pprint
import yaml
import traceback
import csv
import boto3,urllib

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger('example')

# ////////////////////////////////////////////////////////////////////////
def getDataverseInstances():
	# https://dataverse.org/metrics

	if False:
		return [
			{"name": "Demo", "url": "https://demo.dataverse.org/"}
		]

	else:
			
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

	# logger.info(f"GetJSONResponse {query_url}...")
	response=requests.get(query_url,allow_redirects =True, timeout=(30, 600), verify=False)
	# logger.info(f"GetJSONResponse {query_url} DONE")

	if response.status_code!=200:
		raise Exception(f"GetJSONResponse {query_url} response.status_code={response.status_code} not valid {response.reason}")

	ret=json.loads(response.text)

	status=ret.get('status','') 
	if status!='OK':
		raise Exception(f"GetJSONResponse {query_url} status={status} not valid")

	return ret['data']


# //////////////////////////////////////////////////////////////////////
def GetDataverseFiles(max_workers=32, per_page=1000):

	"""
	Example of dataverse file:
	{
		'checksum': {'type': 'MD5', 'value': 'b8dde52d2857e9c8678bf5ce49a125ac'},
		'dataset_citation': 'Harper, Sam, 2015, "Replication Data for: Do Mandatory V2, UNF:6:80e5IlxTWNx+fpFiP/b39g== [fileUNF]',
		'dataset_id': '2716064',
		'dataset_name': 'Replication Data for: Do Mandatory Seat Belt Laws Still Save Lives?',
		'dataset_persistent_id': 'doi:10.7910/DVN/CJPYDG',
		'description': 'Stata dataset of FARS data on motor vehicle crashes.',
		'entity_id': 2861142,
		'file_content_type': 'text/tab-separated-values',
		'file_id': '2861142',
		'file_persistent_id': 'doi:10.7910/DVN/CJPYDG/BNNDSE',
		'file_type': 'Tab-Delimited',
		'md5': 'b8dde52d2857e9c8678bf5ce49a125ac',
		'name': 'fars-data.tab',
		'published_at': '2016-07-27T20:15:32Z',
		'size_in_bytes': 756736,
		'type': 'file',
		'unf': 'UNF:6:0YDFFH131CLTrL8lxvqAjQ==',
		'url': 'https://dataverse.harvard.edu/api/access/datafile/2861142'
	}
	"""

	instances=getDataverseInstances()

	with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

		def SearchApi(base_url,start):
			return 

		# schedule the first page for all
		tasks=[]
		for instance in instances:
			tasks.append((instance["url"],0,3))

		TOTAL,DONE=0,0
		while tasks:
			import random
			random.shuffle(tasks)

			futures={}
			for base_url,start,max_attempt in tasks:
				query_url=f"{base_url}/api/search?q=*&type=file&start={start}&per_page={per_page}&show_entity_ids=true"
				futures[executor.submit(GetJSONResponse, query_url)]=base_url, start, max_attempt, query_url
			tasks=[]
	
			for future in concurrent.futures.as_completed(futures):
				base_url, start, max_attempt, query_url=futures[future]
				try:
					body=future.result()
				except Exception as ex:
					print(f'{query_url} generated an exception: {ex}')
					if max_attempt: 
						tasks.append((base_url,start,max_attempt-1))
					continue

				total,files=int(body['total_count']),body["items"]
				DONE+=len(files)
				
				if start==0:
					TOTAL+=total
					for S in range(per_page, total, per_page):
						tasks.append((base_url,S,max_attempt-1))
						
				logger.info(f"base_url={base_url} {start}/{total} OVERALL {DONE:,}/{TOTAL:,}")

				for file in files:
					yield base_url,file
	

# //////////////////////////////////////////////////////////////////////////////
def NetworkCopy(src, dst, verify=False):

	"""
	See https://amalgjose.com/2020/08/13/python-program-to-stream-data-from-a-url-and-write-it-to-s3/
	"""

	logger.info(f"network-copy {src} {dst}")

	# SRC (todo other cases, eg. src is S3... but in this case we can use )
	if True:	
		assert src.startswith("http://") or src.startswith("https://")
		def HttpSource(url):
			response=requests.get(str(src),stream=True, verify=verify)
			with response as part:
				part.raw.decode_content = True
				yield part.raw
		src_stream=HttpSource(src)

	# DST
	if True:
		parsed=urllib.parse.urlparse(dst)
		assert parsed.scheme=='s3'
		bucket=parsed.netloc
		key=parsed.path.lstrip("/")
		params=urllib.parse.parse_qs(parsed.query)
		profile=params.get("profile",[None])[0]
		endpoint_url=params.get("endpoint-url",[os.environ.get("S3_ENDPOINT_URL")])[0]
		session = boto3.session.Session(profile_name=profile)
		client=session.client('s3', verify=verify,  endpoint_url=endpoint_url)

	# SRC->DST
	if True:
		for chunk in src_stream:
			conf=boto3.s3.transfer.TransferConfig(multipart_threshold=10000, max_concurrency=4)
			client.upload_fileobj(chunk, bucket, key, Config=conf)




# //////////////////////////////////////////////////////////////////////////////////
def Main():

	"""
	To run:
	python3 nsdf/catalog/dataverse.py json
	python3 nsdf/catalog/dataverse.py csv
	python3 nsdf/catalog/dataverse.py stats
	"""

	action=sys.argv[1]

	if action=="json":

		import psutil
		io1 = psutil.net_io_counters()
		T1=time.time()

		# catalog,bucket,filename,filesize,modified,m5
		with open('dataverse.json', 'w') as fout:
			for base_url, file in GetDataverseFiles():
				file["dataverse_url"]=base_url
				fout.write(json.dumps(file) + "\n")
				
		io2 = psutil.net_io_counters()
		print(f"network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")	
		sys.exit(0)

	if action=="csv":
		# catalog,bucket,filename,filesize,modified,m5
		fout=open("dataverse.csv","w") 
		fin=open('dataverse.json',"r")
		writer=csv.writer(fout)
		for line in fin.readlines():
			f=json.loads(line.strip())
			writer.writerow((f.get("dataverse_url",""), f.get("dataset_id",""), f.get("name",""), f.get("size_in_bytes",0), f.get("published_at",""), f.get("md5","")))
		fin.close()
		fout.close()
		sys.exit(0)

	if action=="url":
		# catalog,bucket,filename,filesize,modified,m5
		fin=open('dataverse.json',"r")
		fout=open("dataverse.url.csv","w") 
		writer=csv.writer(fout)
		for line in fin.readlines():
			f=json.loads(line.strip())
			writer.writerow((f.get("url",""),))
		fin.close()
		fout.close()
		sys.exit(0)
		
	if action=="stats":
		# num-files=2,581,397 total-size=124,216,975,466,149 (112TB) min_file_size=0 max-file-size=389,148,288,753 
		with open('dataverse.csv','r') as f:
			csv_reader = csv.reader(f, delimiter=',')
			num_files, total_size,m,M=0,0,sys.maxsize,0
			for row in csv_reader:
				base_url,dataset_ud,name,filesize,published,md5=row
				filesize=max(0,int(filesize))
				total_size+=filesize
				num_files+=1
				m,M=min(m, filesize),max(M, filesize)
		print(f"num-files={num_files:,} total-size={total_size:,} ({total_size//1024**4:,}TB) min_file_size={m:,} max-file-size={M:,} ")
		sys.exit(0)




# //////////////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	Main()


