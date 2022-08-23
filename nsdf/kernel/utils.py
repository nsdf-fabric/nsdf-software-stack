import sys,shutil,os,time,logging, shlex,time,subprocess,io,threading, queue
from urllib.request import AbstractBasicAuthHandler
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("nsdf")

# /////////////////////////////////////////
def GetWorkerId():
	try:
		from requests import get
		ip=get('https://api.ipify.org').text
	except:
		ip="127.0.0.1"

	try:
		from dask.distributed import get_worker
		worker_id =get_worker().id
	except:
		worker_id = 0

	return ip + "-" + str(worker_id)[-3:]

# /////////////////////////////////////////
def SetupLogger(logger, level=logging.INFO, handlers=[]):

	worker_id=GetWorkerId()
	fmt=f"[%(asctime)s][%(levelname)s][%(name)s][%(worker_id)s] %(message)s"

	#datefmt="%Y%m%d %H%M%S"
	datefmt="%H%M%S"

	# see https://discuss.dizzycoding.com/how-do-i-add-custom-field-to-python-log-format-string/
	class AppFilter(logging.Filter):
		def filter(self, record):
			record.worker_id = str(worker_id)
			return True

	logger.addFilter(AppFilter())

	logger.setLevel(level)
	for handler in handlers:
		handler.setLevel(level)
		handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
		logger.addHandler(handler)

	

# /////////////////////////////////////////
def rmdir(dir):
	while os.path.isdir(dir):
		try:
			shutil.rmtree(dir, ignore_errors=False)
		except:
			logger.info(f"Failed to removed directory {dir}, retrying in feww seconds")
			time.sleep(2)
	logger.info(f"Removed directory {dir}")
			
# /////////////////////////////////////////
def ParseUrl(url):
	parsed=urlparse(url)
	qs=parse_qs(parsed.query, keep_blank_values=True)
	return parsed.scheme, parsed.netloc, parsed.path, qs

# /////////////////////////////////////////
def rmfile(file):
	if os.path.isfile(file):
		os.remove(file)

# /////////////////////////////////////////
def is_jupyter_notebook():
	import __main__ as main
	return not hasattr(main, '__file__')

# /////////////////////////////////////////
def clamp(value,a,b):
	if value<a: value=a
	if value>b: value=b
	return value

# /////////////////////////////////////////
def LoadYaml(filename):
	import yaml
	with open(filename) as file:
		body = yaml.load(file, Loader=yaml.FullLoader)	
	return body

# /////////////////////////////////////////////////////////////////////////
def HumanSize(size):
	KiB,MiB,GiB,TiB=1024,1024*1024,1024*1024*1024,1024*1024*1024*1024
	if size>TiB: return "{:.1f}TiB".format(size/TiB) 
	if size>GiB: return "{:.1f}GiB".format(size/GiB) 
	if size>MiB: return "{:.1f}MiB".format(size/MiB) 
	if size>KiB: return "{:.1f}KiB".format(size/KiB) 
	return str(size)

# /////////////////////////////////////////////////////////////////////////
def MakeDirForFile(filename):
	try:
		os.makedirs(os.path.dirname(filename),exist_ok=True)
	except:
		pass

# /////////////////////////////////////////////////////////////////////////////
def WriteCSV(filename,rows):
	import csv
	MakeDirForFile(filename)
	with open(filename, 'wt') as f:
		csv.writer(f).writerows(rows)

# ////////////////////////////////////////////////////////////////////////////
def GetPackageDir():
	import nsdf
	return os.path.dirname(nsdf.__file__)

# ////////////////////////////////////////////////////////////////////////
def GetPackageFilename(path):
	import nsdf
	return os.path.join(GetPackageDir(),path)

# ////////////////////////////////////////////////////////////////////////
def RunCommand(logger, name, cmd, verbose=False, nretry=3):

	args=shlex.split(cmd)
	logger.info(f"RunCommand [{name}] {args} running ...")
	t1 = time.time()

	for I in range(nretry):

		result=subprocess.run(args, 
			shell=False, 
			check=False,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT)

		output=result.stdout.decode('utf-8')

		if verbose: 
			logger.info(output)

		if result.returncode==0:
			break

		error_msg=f"RunCommand [{name}] {args} failed with returncode={result.returncode} output:\n{output}"

		if verbose or I==(nretry-1):
			logger.info(error_msg)

		if I==(nretry-1):
			raise Exception(error_msg)

	sec=time.time()-t1
	logger.info(f"RunCommand [{name}] {args} done in {sec} seconds")


# ////////////////////////////////////////////////////////////////////////
def FileExists(filename):
	if filename.startswith("s3://"):
		from nsdf.s3 import S3
		return S3().existObject(filename)
	else:
		return os.path.isfile(filename)
	
# ////////////////////////////////////////////////////////////////////////
def TouchFile(filename):
	if FileExists(filename):
		return
	if filename.startswith("s3://"):
		from nsdf.s3 import S3
		S3().putObject(filename,"0") # I don't think I can have zero-byte size on S3
	else:
		open(filename, 'a').close()


# ////////////////////////////////////////////////////////////////////////////////////////
def SafeReplaceFile(filename, new_content):

	assert os.path.isfile(filename)

	temp_filename=filename + ".temp"
	if os.path.isfile(temp_filename): 
		os.remove(temp_filename)
	
	os.rename(filename,temp_filename)

	try:
		with open(filename,"wb") as f:
			f.write(new_content)
	except:
		os.rename(temp_filename,filename) # put back the old file
		raise

	# all ok, remove the old file
	os.remove(temp_filename)


# ////////////////////////////////////////////////////////////////
def LoadVault(filename="~/.nsdf/vault/vault.yaml"):
	from nsdf.kernel import LoadYaml
	return LoadYaml(os.path.expanduser(filename))

# ////////////////////////////////////////////////////////////////
def NormalizeEnv(env):
	ret={}
	for k,v in env.items():
		# possibility to include env from a vault account
		if k=="include-vault":
			accounts=v
			assert isinstance(accounts,tuple) or isinstance(accounts,list)
			from nsdf.kernel import LoadYaml
			vault=LoadVault()
			for account in accounts:
				ret={**ret, **NormalizeEnv(vault[account]["env"])}
		else:
			# safety check, only variable names with all capital letters
			assert k.upper()==k 
			ret[k]=v
	return ret

# ////////////////////////////////////////////////////////////////
def PrintEnv(env):
	for k,v in NormalizeEnv(env).items():
		print(f"export {k}={v}")

# ////////////////////////////////////////////////////////////////
def SetEnv(env):
	for k,v in env.items():
		os.environ[k]=str(v)
