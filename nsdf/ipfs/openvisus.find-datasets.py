
from genericpath import isfile
import os,sys
import queue, threading,time
import threading
import yaml
import shutil
import yaml
from bs4 import BeautifulSoup

from OpenVisus import LoadDataset

# ///////////////////////////////////////////////////
def ReadLines(filename, mode="rt"):
	with open(filename,mode) as f:
		return [line.strip() for line in f.readlines() if line.strip()]

# ///////////////////////////////////////////////////
def WriteLines(filename,lines,mode="wt"):
	with open(filename,mode) as f:
		return f.write("\n".join(lines))

# ///////////////////////////////////////////////////
def WriteYaml(filename, d):
	with open(filename, 'w') as f:
		yaml.dump(d, f)

# ///////////////////////////////////////////////////
def ReadYaml(filename):
	with open(filename, 'r') as f:
		return yaml.load(f, Loader=yaml.FullLoader)

# ///////////////////////////////////////////////////
def NextLine(lines,line):
	idx=lines.index(line)
	assert idx>=0
	return lines[idx+1].strip()

# ///////////////////////////////////////////////////
def GetSize(what):
	try: 
		if os.path.isfile(what):
			return os.stat(what)[6]

		if not os.path.isdir(what):
			return 0

		return sum([GetSize(os.path.join(what, it)) for it in os.listdir(what)])
	except:
		return 0
	
# ///////////////////////////////////////////////////
def is_int(str):
	try:
		int(str)
		return True
	except ValueError:
		return False

# ///////////////////////////////////////////////////
def is_float(str):
	try:
		float(str)
		return True
	except ValueError:
		return False

# ////////////////////////////////////////
def GetDatasetInfo(filename):

	try:
		lines=ReadLines(filename)
	
	except OSError as ex:
		raise Exception(f"OSError {ex}")

	except Exception as ex:
		raise Exception(f"Generic Exception {ex}")

	if not len(lines):
		raise Exception("no lines")

	"""
	cat datasets.yaml | grep "version: " | sort --unique
	version: -1
	version: 2
	version: 3
	version: 4
	version: 5
	version: 6
	"""

	# new xml format
	if lines[0].startswith("<dataset"):
		with open(filename, 'r') as f:  
			body = BeautifulSoup(f.read(), "xml")
		version=body.find("idxfile").find("version")["value"]
		template=body.find("idxfile").find("filename_template")["value"]

	elif "(version)" in lines and "(filename_template)" in lines:
		version=NextLine(lines,"(version)")
		template=NextLine(lines,"(filename_template)")

	elif "(rootpath)" in lines: 
		if "(version)" in lines:
			version=NextLine(lines,"(version)")
		else:
			version="-1" # not sure if they are compatible with v5
		
		template=NextLine(lines,"(rootpath)")

	else:
		raise Exception("cannot find version or template")

	if not is_int(version):

		# example 6.1 (new Duong stuff)
		if is_float(version):
			raise Exception(f"float version {version}")

		raise Exception(f"not integer version {version}")

	# this expression works even if there is no % in the template and it's a file
	bin=os.path.abspath(os.path.join(os.path.dirname(filename), template.split("%")[0])) 

	size=GetSize(bin)
	if not size: 
		raise Exception(f"{bin} does not exist ")

	try:
		LoadDataset(filename)
		open=True
	except:
		open=False

	return {
		"filename": filename, 
		"version": int(version), 
		"bin": bin, 
		"size": size,
		"open": open
	}

# ////////////////////////////////////////////////////////////////////////
def RunInParallel(tasks, nworkers=64):

	q = queue.Queue()

	def Worker(q):
		while True:
			fun = q.get()
			if fun is None:   break
			fun()
			q.task_done()

	workers = []
	for id in range(nworkers):
		worker = threading.Thread(target=Worker, args=(q,))
		worker.start()
		workers.append(worker)

	for task in tasks:
		q.put(task)

	for worker in workers: 
		q.put(None)
	
	for worker in workers: 
		worker.join()


# ////////////////////////////////////////////////////////////////////
def SaveDatasets(datasets,filename="./datasets.yaml"):

	print("Saving datasets to",filename,"...")

	ok    =[it for it in datasets if not "error" in it]
	errors=[it for it in datasets if     "error" in it]

	# print out ok
	bytes_ok=sum([it["size"] for it in ok])
	
	# just ignore datasets with permission denied nothing I can do
	errors=[it for it in errors if "Permission denied" not in it["error"]]
	
	# directory does not exist, not much I can do
	errors=[it for it in errors if "does not exist" not in it["error"]]

	print("#ok",len(ok),"bytes_ok",bytes_ok,"bytes",int(bytes_ok/1024**3),"GB")
	print("#errors",len(errors))

	# do the real saving
	WriteYaml(f"{filename}.new",ok+errors)
	shutil.move(f"{filename}.new",filename)
	print("Saved file", filename)

# ////////////////////////////////////////////////////////////////////////
def Main():

	if not os.path.isfile("datasets.yaml"):
		t1=time.time()
		datasets=[{
			"filename": filename
		} for filename in ReadLines("datasets.txt")  if ".git" not in filename and "javapi" not in filename and "Adobe/Acrobat" not in filename]

		WriteYaml("datasets.yaml",datasets)
		print("Generated first datasets in",time.time()-t1,"seconds")

	if False:
		t1=time.time()
		datasets=ReadYaml("datasets.yaml")
		print("ReadYaml returned",len(datasets),"datasets in",time.time()-t1,"seconds")

		# filter basename
		datasets=[it for it in datasets if not os.path.basename(it["filename"]).startswith("._")]

		tasks=[]
		last_saved=time.time()
		for index,dataset in enumerate(datasets):

			filename=dataset["filename"]

			# already done without errors? (i.e. I will retry the errors)
			if not "error" in dataset: 
				continue

			def GetDatasetInfoTask(index, filename):

				try:
					dataset=GetDatasetInfo(filename)
				except Exception as ex:
					dataset={"filename": filename, "error": str(ex)}

				nonlocal datasets
				datasets[index]=dataset
				print(threading.get_ident(),dataset)
				
				# save every x seconds
				if False:
					nonlocal last_saved
					if (time.time()-last_saved) > 30:
						last_saved=time.time()
						SaveDatasets(datasets)
						last_saved=time.time()

			tasks.append(lambda index=index, filename=filename: GetDatasetInfoTask(index,filename))

		RunInParallel(tasks)
		SaveDatasets(datasets)

# ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
if __name__ == "__main__":
	Main()
