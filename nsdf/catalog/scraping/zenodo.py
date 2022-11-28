"""

using zenodopy client (https://github.com/lgloege/zenodopy).

Important to mention:
- each API request cannot return more than 10K items, so I am doing the queries partitioning the time from 20100101 to today() with a delta-days of 5
- with a delta of 5 days we do (2022-2010)*365/5=~876 network requests
- probably using a delta larger we could get better numbers, but I found certain period of 5 days with more than 10K records
- there is a rate limiter of 60 requests per minute and 2000 requests per hour (33 req/min), so I am using an overall 30 calls/min

Rate limiter code:
```
from tkinter import E
from ratelimit import limits, RateLimitException, sleep_and_retry

@sleep_and_retry
@limits(calls=30, period=60) 
def GetJSONResponse(url):
	... code here..
```

Statistics
- num-datasets=1,012,474 (NOTE: using DOI as it was a dataset)
- num-records=3,485,074 (3M)
- tot-size=373,890,709,078,423 (373TB)
- network-upload-bytes=46,367,940 (46MB)
- network-download-bytes=4,238,454,624 (4GB)
- total-seconds=19734 (5.4 hours)

"""

import os,sys,requests,time, datetime,urllib3
import zenodopy
from pprint import pprint
import json, csv

# I can use the guest account, it has some limitation bgut will be fine to get public records
zeno = zenodopy.Client()

# /////////////////////////////////////////////////////////////
# ZENODO Global limit for guest users	60 requests per minute, 2000 requests per hour (==max overall 30 request per 60 seconds)
# see # https://developers.zenodo.org/
# https://akshayranganath.github.io/Rate-Limiting-With-Python/
# /////////////////////////////////////////////////////////////
# from tkinter import E
from ratelimit import limits, RateLimitException, sleep_and_retry

@sleep_and_retry
@limits(calls=30, period=60) 
def GetJSONResponse(url):
	ret=requests.get(url, verify=True, timeout=(10,60))
	if ret.status_code!=200:
		raise Exception(f"Cannot get response for url={url} got {ret.status_code} {ret.reason}")
	return ret

# this is an hard limit imposed by the Zenodo Search API that is using ElasticCache
ZENODO_MAX_RECORDS=10000

# /////////////////////////////////////////////////////////////
def GetZenodoRecords(a,b):

	# create the url with the condition on publication_date
	d1=datetime.date.fromordinal(a)
	d2=datetime.date.fromordinal(b)
	m=f"{d1.year}-{d1.month:02d}-{d1.day:02d}"
	M=f"{d2.year}-{d2.month:02d}-{d2.day:02d}"
	url=requests.Request('GET','https://zenodo.org/api/records', params={
		'q': '(publication_date: ["%s" TO "%s"})' % (m,M), # first date is included, second data is excluded
		'sort': 'publication_date',
		'status': 'published', 
		'size' : ZENODO_MAX_RECORDS,
		'page' : '1'
		}).prepare().url

	
	# try several times...
	t1=time.time()
	#print(f"starting requests d1={d1} d2={d2} delta={b-a} ...")
	for retry in range(3):
		try:
			response=GetJSONResponse(url).json()
			break
		except Exception as ex:
			# too many retries
			if retry==2: 
				raise

	total=response['hits']['total']
	print(f"Got response d1={d1} d2={d2} delta={b-a} in {time.time()-t1:.2f} seconds #records={total}")

	# am I getting all hits?
	if  total<ZENODO_MAX_RECORDS:
		return response['hits']['hits']

	# failed, need to try with lower delta
	delta=b-a
	if delta==1:
		raise Exception(f"Cannot do much, got #records={total} with delta={delta}")

	delta=max(1,delta//2)
	print(f"Got Too many records, reducing delta={delta}")
	ret=[]
	for d in range(a,b,delta):
		ret.extend(GetZenodoRecords(d,min(d+delta,b)))
	return ret

# /////////////////////////////////////////////////////
"""
{'conceptdoi': '10.5281/zenodo.3234155',
 'conceptrecid': '3234155',
 'created': '2019-05-28T23:20:04.663116+00:00',
 'doi': '10.5281/zenodo.3234156',
 'files': [{'bucket': '2c6022e0-2c31-4cc6-b677-374bb17b3ca7',
            'checksum': 'md5:55b1d56a6d9adb9e431a01fb5f91f791',
            'key': 'wlodarczak_etal_2010_entailed_feedback.pdf',
            'links': {'self': 'https://zenodo.org/api/files/2c6022e0-2c31-4cc6-b677-374bb17b3ca7/wlodarczak_etal_2010_entailed_feedback.pdf'},
            'size': 87621,
            'type': 'pdf'}],
 'id': 3234156,
 'links': {'badge': 'https://zenodo.org/badge/doi/10.5281/zenodo.3234156.svg',
           'bucket': 'https://zenodo.org/api/files/2c6022e0-2c31-4cc6-b677-374bb17b3ca7',
           'conceptbadge': 'https://zenodo.org/badge/doi/10.5281/zenodo.3234155.svg',
           'conceptdoi': 'https://doi.org/10.5281/zenodo.3234155',
           'doi': 'https://doi.org/10.5281/zenodo.3234156',
           'html': 'https://zenodo.org/record/3234156',
           'latest': 'https://zenodo.org/api/records/3234156',
           'latest_html': 'https://zenodo.org/record/3234156',
           'self': 'https://zenodo.org/api/records/3234156'},
 'metadata': {'access_right': 'open',
              'access_right_category': 'success',
              'creators': [{'affiliation': 'Bielefeld University',
                            'name': 'Marcin Włodarczak',
                            'orcid': '0000-0003-3824-2980'},
                           {'affiliation': 'Tilburg University',
                            'name': 'Harry Bunt'},
                           {'affiliation': 'Tilburg University',
                            'name': 'Volha Petukhova'}],
              'description': '<p>In this paper we investigate relationships '
                             'between entailment relations among communicative '
                             'functions and dominance judgements in an '
                             'annotation task in which participants are '
                             'instructed to rank utterance functions in terms '
                             'of their importance. It is hypothesised that on '
                             'average entailed functions should be assigned '
                             'lower ranks than entailing functions. '
                             'Preliminary results of an experiment are '
                             'reported for positive auto-feedback functions '
                             'which are argued to be entailed by '
                             'backward-looking functions such as Confirm.</p>',
              'doi': '10.5281/zenodo.3234156',
              'language': 'eng',
              'license': {'id': 'CC-BY-4.0'},
              'publication_date': '2010-01-01',
              'related_identifiers': [{'identifier': '10.5281/zenodo.3234155',
                                       'relation': 'isVersionOf',
                                       'scheme': 'doi'}],
              'relations': {'version': [{'count': 1,
                                         'index': 0,
                                         'is_last': True,
                                         'last_child': {'pid_type': 'recid',
                                                        'pid_value': '3234156'},
                                         'parent': {'pid_type': 'recid',
                                                    'pid_value': '3234155'}}]},
              'resource_type': {'subtype': 'conferencepaper',
                                'title': 'Conference paper',
                                'type': 'publication'},
              'title': 'Entailed feedback: Evidence from a ranking experiment'},
 'owners': [58863],
 'revision': 5,
 'stats': {'downloads': 16.0,
           'unique_downloads': 12.0,
           'unique_views': 97.0,
           'version_downloads': 16.0,
           'version_unique_downloads': 12.0,
           'version_unique_views': 97.0,
           'version_views': 108.0,
           'version_volume': 1401936.0,
           'views': 108.0,
           'volume': 1401936.0},
 'updated': '2020-01-20T15:22:18.773179+00:00'}

"""

# /////////////////////////////////////////////////////
if __name__=="__main__":
	"""
	python3 nsdf/catalog/zenodo.py zenodo.json
 	python3 nsdf/catalog/zenodo.py zenodo.csv
	"""
   
	action=sys.argv[1]


   # /////////////////////////////////////////////////////
	if action=="zenodo.json":
		RECORDS=[]
		long_ago=datetime.date(2010, 1, 1).toordinal() #  I am loosing some Zenodo records but with wrong date
		today=datetime.datetime.today().toordinal()

		import psutil
		io1 = psutil.net_io_counters()
		T1=time.time()

		# choose the delta in a way that you don't get more than 10K records for a request
		delta=5

		for A in range(long_ago,today,delta):
			B=min(today,A+delta)
			try:
				RECORDS.extend(GetZenodoRecords(A,B))
			except Exception as ex:
				print(f"ERROR A={A} B={B} exception={ex}")

		io2 = psutil.net_io_counters()
		print(f"num-network-upload-bytes={io2.bytes_sent - io1.bytes_sent:,} network-download-bytes={io2.bytes_recv - io1.bytes_recv:,} sec={time.time()-T1:.2f}")	

		with open("zenodo.json", 'w') as fp:
			json.dump(RECORDS, fp)
	
		print("ALl done")
		sys.exit(0)
   
   # /////////////////////////////////////////////////////
	if action=="zenodo.csv":

		with open("zenodo.json", 'r') as fin:
			RECORDS=json.load(fin)

		with open("zenodo.csv","w")  as fout:
			writer=csv.writer(fout)
			num_files,tot_size=0,0
			for record in RECORDS:
				for f in record.get('files',[]):

					def Encode(value):
						return str(value).replace(","," ").replace("'"," ").replace('"'," ").replace("  "," ")
					
					writer.writerow([
						"zenodo.org",                  # catalog
						record.get("conceptdoi","na"), # bucket
						Encode(f.get("key","")),       # filename
						f.get("size",0),               # size
						record.get("created",""),      # creation time and/or modification time
						f.get("checksum","")           # checksum
					])   
					num_files+=1
					tot_size+=f.get("size",0)
			print("num_files",num_files,"tot_size",tot_size)
		sys.exit(0)