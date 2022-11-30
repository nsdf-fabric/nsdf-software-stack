import os,sys,time,datetime,threading,queue,math
import panel as pn
import numpy as np
import ipywidgets
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from clickhouse_driver import connect,Client
import OpenVisus as ov

# this is needed to show matplot plots inside panel
# https://panel.holoviz.org/reference/panes/Matplotlib.html
pn.extension('ipywidgets')
pn.extension(sizing_mode='stretch_width')

# //////////////////////////////////////////////////////////////////////////////////////
class StringUtils:

	@staticmethod
	def ConvertNum(value):
		if value == 0: return "0"
		unit = ("", "thousands", "millions", "bilions")
		i = min(len(unit)-1,int(math.floor(math.log(value, 1000))))
		s = round(value / math.pow(1000, i),2)
		return f"{s} {unit[i]}"

	@staticmethod
	def ConvertSize(value):
		if value == 0: return "0"
		unit = ("", "KiB", "MiB", "GiB", "TiB", "PiB")
		i = min(len(unit)-1,int(math.floor(math.log(value, 1024))))
		s = round(value / math.pow(1024, i),2)
		return f"{s} {unit[i]}"

# //////////////////////////////////////////////////////////////////////////////////////
class NSDFCatalogDashboard:

	# constructor
	def __init__(self):

		default_catalog      =str(pn.state.session_args.get("catalog",""))
		default_limit        =str(pn.state.session_args.get("limit","1000"))
		default_show_catalog =bool(pn.state.session_args.get("show_catalog",True))
		default_show_bucket  =bool(pn.state.session_args.get("show_bucket",True))
		default_show_ext     =bool(pn.state.session_args.get("show_ext",False))

		self.client=Client(
			host= os.environ["CLICKHOUSE_HOST"], 
			port=str(os.environ["CLICKHOUSE_PORT"]), 
			user=os.environ["CLICKHOUSE_USER"], 
			password=os.environ["CLICKHOUSE_PASSWORD"], 
			secure= os.environ["CLICKHOUSE_SECURE"])  
  
		# https://panel.holoviz.org/gallery/simple/sync_location.html#simple-gallery-sync-location
  
		# total records and total size
		NUM_FILES,TOT_BYTES=self.client.execute(f"SELECT SUM(num_files),SUM(tot_size) FROM nsdf.aggregated_catalog;")[0]
  
		self.catalogs=[it[0] for it in self.client.execute("SELECT DISTINCT catalog from nsdf.catalog")]
		self.catalog  = pn.widgets.Select(name='', options=['*'] + self.catalogs,value=default_catalog)
		self.catalog.param.watch(lambda evt: self.refresh(), 'value')
  
		self.limit = pn.widgets.Select(options=["100","1000","10000"],value=default_limit) # ,"Unlimited" DISABLED FOR now
		self.limit.param.watch(lambda evt: self.refresh(), 'value')  
  
		self.show={}
		self.show["catalog"] = pn.widgets.Checkbox(name='Catalog'  ,value=default_show_catalog)
		self.show["bucket" ] = pn.widgets.Checkbox(name='Bucket'   ,value=default_show_bucket)
		self.show["ext"    ] = pn.widgets.Checkbox(name='Extension',value=default_show_ext)
		for k,widget in self.show.items():
			widget.param.watch(lambda evt: self.refresh(), 'value')
  
		self.tabulator=pn.widgets.Tabulator(pagination='remote',page_size=10)  
  
		def T(s) : return pn.widgets.input.StaticText(value=s)

		self.query = pn.widgets.input.TextAreaInput(height=160)
		self.status = T("Ready to run a query");

		self.run_button = pn.widgets.Button(name='Run', button_type='primary')
		self.run_button.on_click(lambda evt: self.runQuery())

		self.material = pn.template.MaterialTemplate(title='NSDF-Catalog') # ,theme="dark"

		self.material.main.append(
    	pn.Column(
				pn.pane.Markdown(f"""Total size **{StringUtils.ConvertSize(TOT_BYTES)}** Number of records **{StringUtils.ConvertNum(NUM_FILES)}**"""),
				
				pn.Row(T("Catalog"),self.catalog,T("Limit"),self.limit,T("Show"),
           pn.Column(self.show["catalog"],self.show["bucket"],self.show["ext"]),width=1024),
				pn.Row(T("Status"),self.status,width=1024),
				pn.Row(T("Query"),pn.Row(self.query,width=600),self.run_button,width=1024),
				pn.Row(self.tabulator),
				width=1024
			))
  
		pn.state.location.sync(self.catalog        , {'value': 'catalog'})
		pn.state.location.sync(self.limit          , {'value': 'limit'})
		pn.state.location.sync(self.show["catalog"], {'value': 'show_catalog'})
		pn.state.location.sync(self.show["bucket"] , {'value': 'show_bucket'})
		pn.state.location.sync(self.show["ext"]    , {'value': 'show_ext'})
  
		self.refresh()

	# runQuery
	def runQuery(self):
		# pn.param.ParamMethod.loading_indicator = True
		self.status.value=f"Running query..."
		t1=time.time()
		records=self.client.execute(self.query.value)
		sec=time.time()-t1
		df=pd.DataFrame(records)
		self.tabulator.value=df
		self.tabulator.hidden_columns=["index"] 
		self.tabulator.titles={I:self.titles[I] for I in range(len(self.titles))}
		self.status.value=f"Elapsed {int(sec)} seconds num_records={len(records):,}"

	# showRecords
	def refresh(self):
		group_by=[key for key in self.show if self.show[key].value]
		select=group_by + ['SUM(tot_size) as tot_size','SUM(num_files) as num_files']
		conditions=[f"catalog='{self.catalog.value}'"] if self.catalog.value!="*" else ["1=1"]
		conditions=' AND '.join(conditions)
		limit="" if self.limit.value=="Unlimited" else f"LIMIT {self.limit.value}"
		query=f"""
SELECT {', '.join(select)}
FROM nsdf.aggregated_catalog
WHERE {conditions}
GROUP BY {', '.join(group_by)}
ORDER BY {'tot_size DESC, num_files DESC'}
{limit}
		"""
		self.query.value=query
		self.titles=[it for it in [
			"Catalog"   if "catalog" in select else "",
			"Bucket"    if "bucket"  in select else "",
			"Extension" if "ext"     in select else "",
			"tot_size",
			"num_files"
		] if it]
		self.runQuery()
		return



# //////////////////////////////////////////////////////////////////////////////////////
if True:
	exp=NSDFCatalogDashboard()
	exp.material.servable()

