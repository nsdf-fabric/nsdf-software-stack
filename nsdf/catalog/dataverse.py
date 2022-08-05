
import csv,json,requests,os,sys, threading, time
import concurrent.futures
from pprint import pprint
import yaml
import traceback
import csv


# //////////////////////////////////////////////////////////////////////
def ProduceYaml(output_filename, max_workers=64,):

	"""
	this function scrape all the following DataVerse instances and create a Yaml 'dataverse.yaml' file
	with the total number of files
	if case of error, the yaml file contains an error message explaining what went wrong
	"""

	# https://dataverse.org/metrics
	instances=[
		{"name": "Abacus", "url": "http://abacus.library.ubc.ca"},
		{"name": "ACSS Dataverse", "url": "http://dataverse.theacss.org"},
		{"name": "Arca Dados", "url": "http://dadosdepesquisa.fiocruz.br"},
		{"name": "ASU Library Research Data Repository", "url": "http://dataverse.asu.edu"},
		{"name": "AUSSDA Dataverse", "url": "http://data.aussda.at"},
		{"name": "Borealis", "url": "http://borealisdata.ca"},
		{"name": "CIFOR", "url": "http://data.cifor.org"},
		{"name": "CIMMYT Research Data", "url": "http://data.cimmyt.org"},
		{"name": "CIRAD Dataverse", "url": "http://dataverse.cirad.fr"},
		{"name": "CORA. Research Data Repository (RDR)", "url": "http://dataverse.csuc.cat"},
		{"name": "CROSSDA", "url": "http://data.crossda.hr"},
		{"name": "CUHK Research Data Repository", "url": "http://researchdata.cuhk.edu.hk"},
		{"name": "Dartmouth Dataverse", "url": "http://dataverse.dartmouth.edu"},
		{"name": "DaRUS", "url": "http://darus.uni-stuttgart.de"},
		{"name": "Data INRAe", "url": "http://data.inrae.fr"},
		{"name": "Data Suds", "url": "http://dataverse.ird.fr"},
		{"name": "data.sciencespo", "url": "http://data.sciencespo.fr"},
		{"name": "Dataverse e-cienciaDatos", "url": "http://edatos.consorciomadrono.es"},
		{"name": "DataverseNL", "url": "http://dataverse.nl"},
		{"name": "DataverseNO", "url": "http://dataverse.no"},
		{"name": "DR-NTU (Data)", "url": "http://researchdata.ntu.edu.sg"},
		{"name": "Florida International University Research Data Portal", "url": "http://dataverse.fiu.edu"},
		{"name": "George Mason University Dataverse", "url": "http://dataverse.orc.gmu.edu"},
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

	def MyTask(url):
		query_url=f"{url}/api/search?q=*&type=file&start=0&per_page=1"
		# print(threading.current_thread().name,query_url)
		try:
			response=requests.get(query_url,allow_redirects =True, timeout=(10, 100))
			if response.status_code==200:
				data=json.loads(response.text)['data']
				total=data['total_count']
				return (total,"")
			else:
				return (0,response.reason)
		except Exception as ex:
			return (0,str(ex))

	with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers,thread_name_prefix='my-thread-') as executor:
		futures = []
		for I,it in enumerate(instances):
			url=it["url"]
			futures.append(executor.submit(lambda url=url,I=I: [I,url, *MyTask(url)]))
		
		for future in concurrent.futures.as_completed(futures):
			I,url,total,error_msg=future.result()
			instances[I]["total"]=total
			if error_msg:
				instances[I]["error_msg"]=error_msg
			pprint(instances[I])


	with open(output_filename, 'w') as file:
		yaml.dump(instances, file)



# //////////////////////////////////////////////////////////////////////
def GetFiles(input_filename, output_filename, max_workers=64, per_page=1000):

	"""
	produce a CSV file with all files from all dataverse instances
	NOTE: I split the total-file range in several chunked request
	      for now I do not worry too much of errors and I just ignore them
	"""

	def MyTask(url, start, per_page):
		# see https://guides.dataverse.org/en/4.18.1/api/search.html
		query_url = f"{url}/api/search?q=*&type=file&start={start}&per_page={per_page}"
		tname=threading.current_thread().name
		print(f"[{tname}] BEGIN {query_url} {start}...")
		try:
			response=requests.get(query_url,allow_redirects =True, timeout=(10, 100))
			if response.status_code!=200:
				print(f"ERROR {query_url} got status_code={response.status_code} error_msg={response.reason} ")
				return []
			else:
				data=json.loads(response.text)
				ret=[(
						url, # catalog
						file["dataset_id"],  # bucket
						file["name"],  #filename
						file["size_in_bytes"], #size
						file["published_at"],  # last-modification
						file["md5"]
						) for file in data['data']['items']]
				print(f"[{tname}] DONE {query_url} {start}")
				return ret
		except Exception as ex:
			# print(f"ERROR {query_url} exception {traceback.format_exc()}")
			print(f"[{tname}] ERROR-A {query_url} exception {ex}")
			return []

	with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
		
		with open(input_filename) as f:
			instances = yaml.load(f, Loader=yaml.FullLoader)

		tasks=[]
		for I,it in enumerate(instances):
			url,total=it["url"],it["total"]
			sub=[]
			for start in range(0, total, per_page):
				sub.append(lambda I=I, url=url,start=start,per_page=per_page: [I,url,start, MyTask(url,start,per_page)])
			tasks.append(sub)

		# do not want too many connecftion on the same server at the same time
		import itertools
		tasks=[x for x in itertools.chain(*itertools.zip_longest(*tasks)) if x is not None]
		futures = []
		for task in tasks:
			futures.append(executor.submit(task))

		with open(output_filename,"w") as f:
			writer=csv.writer(f)
			ndone=0
			t1=time.time()
			for future in concurrent.futures.as_completed(futures):
				try:
					I,url,start,files=future.result()
					ndone+=1
					done_per_sec=(time.time()-t1)/ndone
					remaining=len(tasks)-ndone
					eta=int(remaining/done_per_sec)
					writer.writerows(files)
					f.flush()
					print(url,start, len(files),"remaining",remaining, "eta", eta)
				except Exception as ex:
					# print(f"ERROR {traceback.format_exc()}")
					print(f"ERROR-b {ex}")


#ProduceYaml('dataverse.yaml')

# TODO: lots of problems with  http://dataverse.harvard.edu, I am getting lots of read timeout 
GetFiles('dataverse.yaml', "dataverse.csv")