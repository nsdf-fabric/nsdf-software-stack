import struct, os, sys, time, datetime
import yaml # pyyaml package
import logging

KB,MB,GB=1024, 1024*1024, 1024*1024*1024

from multiprocessing.dummy import Pool as ThreadPool 

# //////////////////////////////////////////////////////////////////////
def Check(cond,msg=""):
	if not cond:
		logging.info(f"check failed {msg}")
		raise Exception(f"check failed {msg}")

# //////////////////////////////////////////////////////////////////////
def GetArg(args,key,default_value=""):
	key=key.lstrip("-")
	for I in range(len(args)-1):
		current_key=args[I].lstrip("-")
		if current_key==key:
			return args[I+1].strip()
	return default_value

# //////////////////////////////////////////////////////////////////////
def ReadTextFile(filename):
	""" read all file as a string"""
	with open(filename, 'r') as file:
		return file.read() 

# //////////////////////////////////////////////////////////////////////
def ReadYamlFile(filename):
	with open(filename, 'r') as f:
		return yaml.load(f, Loader=yaml.FullLoader)



# //////////////////////////////////////////////////////////////////////
def WriteBinaryFile(filename,body):
	try:
		os.makedirs(os.path.dirname(filename),exist_ok=True)
	except:
		pass

	try:
		os.remove(filename)
	except Exception as e:
		pass

	f=open(filename, "wb")
	f.write(body)	
	f.close()

# //////////////////////////////////////////////////////////////////////
def WriteTextFile(filename,body):
	try:
		os.makedirs(os.path.dirname(filename),exist_ok=True)
	except:
		pass

	try:
		os.remove(filename)
	except Exception as e:
		pass

	f=open(filename, "wt")
	f.write(body)	
	f.close()

# //////////////////////////////////////////////////////////////////////
def GetRandomString(length):
	# choose from all lowercase letter
	letters = string.ascii_lowercase
	return ''.join(random.choice(letters) for i in range(length))

# //////////////////////////////////////////////////////////////////////
def ParallelRun(fn,args, serial=False):
	N=len(args)
	if N==0: return []

	if serial:
		ret=[]
		for I in range(N):
			ret.append(fn(args[I]))
		return ret
	else:
		pool = ThreadPool(N)
		ret=pool.map(fn, args)
		pool.close()
		pool.join()
		return ret
	
# //////////////////////////////////////////////////////////////////////
def AppendCSV(output_filename, row):
	f=open(output_filename, 'a', newline='')
	writer = csv.writer(f)
	writer.writerow(row)
	f.close()

# //////////////////////////////////////////////////////////////////////
def Deindent(text):
	import textwrap3
	return textwrap3.dedent(text).strip()


__vault__=None

# //////////////////////////////////////////////////////////////////////
def GetConfig(account):
	global __vault__
	if __vault__ is None:
		VAULT_DIR=os.path.expanduser("~/.nsdf/vault")
		# I am expeting a global vault file heres
		filename=os.path.realpath(os.path.join(VAULT_DIR,"vault.yaml"))
		Check(os.path.isfile(filename),f"cannot find config file {filename}")
		body=ReadTextFile(filename)
		body=body.replace("${CURRENT_DIRECTORY}",os.path.dirname(filename))
		__vault__=yaml.load(body, Loader=yaml.FullLoader)
	return __vault__[account]