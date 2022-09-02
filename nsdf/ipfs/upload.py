import os,sys,time, subprocess, shlex



# /////////////////////////////////////////
def ExecuteShellCommand(cmd):
	for I in range(9999999999):
		print(cmd)
		result = subprocess.run(cmd, check=False, shell=True)
		print("   result:", result)
		print("   stdout:", result.stdout)
		print("   stderr:", result.stderr)
		if result.returncode==0: return
		time.sleep(1)
	raise Exception("command failed")

# /////////////////////////////////////////
def Touch(filename):
	os.makedirs(os.path.dirname(filename),exist_ok=True)
	with open(filename,"w") as fout:
		fout.write(str(time.time()))

# /////////////////////////////////////////
def CollectRemotes():
		
	dirs=[]

	# 242.3G 
	dirs.append((0,"s3://Pania_2021Q3_in_situ_data/radiographic_scan/"))
 
	# 441.3G (TOO BIG for my hard disk)
	# dirs.append((0,"s3://Pania_2021Q3_in_situ_data/hdf5/"))

	h5_1=sorted([line.strip() for line in f"""
	112509 112512 112515 112517 112520 112522 112524 112526 112528 112530 112532 112545 112548 112550 112552 112554 
	112556 112558 112560 112577 112579 112581 112583 112585 112587 112589 112591 112593 112595 112597 112599 112601
	112603"""
	.split() if line.strip()])
	for h5 in h5_1:
		for I,it in enumerate(["modvisus","16mb/", "8mb/", "4mb/", "2mb/", "1mb/", "512kb/", "256kb/", "128kb/", "64kb/", "32kb/"]):
			if it=="modvisus": continue # it does not exist
			dirs.append((I,f"s3://Pania_2021Q3_in_situ_data/idx/fly_scan_id_{h5}.h5/reconstructions/arco/{it}"))

	h5_2=sorted([line.strip() for line in f"""
	112437 112441 112443 112451 112453 112455 112458 112461 112464 112467 112470 112475 112478 112482 112484 112487
	112489 112491 112493 112495 112500 112502 112504 112509 112512 112515 112517 112520 112522 112524 112526 112528
	112530 112532 112545 112548 112550 112552"""
	.split() if line.strip()])

	for h5 in h5_2 :
		for a in ("r/","s/"):
			dirs.append((0,f"s3://Pania_2021Q3_in_situ_data/workflow/fly_scan_id_{h5}.h5/{a}tif/"))
    
			for I,it in enumerate(["modvisus/", "16mb/", "8mb/", "4mb/", "2mb/","1mb/"]):
				dirs.append((I,f"s3://Pania_2021Q3_in_situ_data/workflow/fly_scan_id_{h5}.h5/{a}idx/{it}"))

	dirs.sort()
	dirs=[b for a,b in dirs]
	return dirs

# /////////////////////////////////////////
if __name__=="__main__":

	"""
	ssh -i ~/.nsdf/vault/id_nsdf_jhu nsdf01 
	cd /mnt/shared/nsdf/nsdf-software-stack/
	curl -L https://github.com/peak/s5cmd/releases/download/v2.0.0/s5cmd_2.0.0_Linux-64bit.tar.gz | sudo tar xz -C /usr/bin
	screen

	nsdf2# WORKER_ID=0 NUM_WORKERS=5 python3 nsdf/ipfs/upload.py
	nsdf3# WORKER_ID=1 NUM_WORKERS=5 python3 nsdf/ipfs/upload.py
	nsdf4# WORKER_ID=2 NUM_WORKERS=5 python3 nsdf/ipfs/upload.py
	nsdf5# WORKER_ID=3 NUM_WORKERS=5 python3 nsdf/ipfs/upload.py
	nsdf6# WORKER_ID=4 NUM_WORKERS=5 python3 nsdf/ipfs/upload.py
 
	# each directory is ~50GB , total drectories 862 , overall 43TB
	# 510 done so far
	while [[ 1 == 1 ]] ; do (find /mnt/shared/.done/ -type f | wc -l) && sleep 60 ; done
	"""

	WORKER_ID=int(os.environ.get("WORKER_ID",0))
	NUM_WORKERS=int(os.environ.get("NUM_WORKERS",1))
	print("WORKER_ID",WORKER_ID,"NUM_WORKERS",NUM_WORKERS)

	remotes1=CollectRemotes()
	for I,remote1 in enumerate(remotes1):
		
		# I can run in parallel
		if (I % NUM_WORKERS) != WORKER_ID: 
			continue
  
		# remote1 ==                    s3://Pania_2021Q3_in_situ_data/radiographic_scan/
		# key     ==                         Pania_2021Q3_in_situ_data/radiographic_scan/
		# local   == /srv/nvme0/nsdf/buckets/Pania_2021Q3_in_situ_data/radiographic_scan/
		# remote2 ==       s3://utah/buckets/Pania_2021Q3_in_situ_data/radiographic_scan/
		key=remote1[5:] 
		local=f"/srv/nvme0/nsdf/buckets/{key}"
		remote2=f"s3://utah/buckets/{key}"
	 
		print(f"# {I}/{len(remotes1)} Syncing {remote1} {local} {remote2}...")
	 
		done_filename=f"/mnt/shared/.done/{key}/done"
		if os.path.isfile(done_filename):
			print(f"# Skipping {done_filename} exists")
		else:
			ExecuteShellCommand(f"AWS_PROFILE=wasabi      s5cmd --numworkers 64 --endpoint-url https://s3.us-west-1.wasabisys.com                        cp --if-size-differ '{remote1}*' '{local}'")
			ExecuteShellCommand(f"AWS_PROFILE=sealstorage s5cmd --numworkers 64 --endpoint-url https://maritime.sealstorage.io/api/v0/s3 --no-verify-ssl cp --if-size-differ '{local}*' '{remote2}'")
			Touch(done_filename)
			ExecuteShellCommand(f"rm -Rf {local}")
  
