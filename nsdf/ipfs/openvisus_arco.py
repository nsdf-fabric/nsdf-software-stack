
from genericpath import isfile
import os,sys
import queue, threading,time
import threading
import yaml
import shutil
import yaml
from yaml import CLoader

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
		return yaml.load(f, Loader=yaml.CLoader)
	

# /////////////////////////////////////////
def Touch(filename):
	os.makedirs(os.path.dirname(filename),exist_ok=True)
	with open(filename,"w") as fout:
		fout.write(str(time.time()))

# ////////////////////////////////////////////////////////////////////////
def Main():

	t1=time.time()
	datasets=ReadYaml("nsdf/ipfs/openvisus.datasets.ok.yaml")

	for it in datasets:
		src=it["filename"]
		dst="s3://utah/arco/{src}"
  
   # todo...
		# see nsdf.convert Main function


# ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
if __name__ == "__main__":
	Main()
