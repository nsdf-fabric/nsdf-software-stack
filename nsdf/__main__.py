import os,sys,time
from nsdf.kernel import NormalizeEnv, PrintEnv, SetEnv, LoadVault

# ////////////////////////////////////////////////////
def Main(args):

	action=args[1]
 
 	# _________________________________________
	if action=="s3":
		import nsdf.s3
		return nsdf.s3.Main([args[0]] + args[2:])
 
	# _________________________________________
	if action=="export-env":
		"""
		python3 -m nsdf export-env s3-wasabi
		"""
		account=args[args.index( "export-env")+1]
		
		vault=LoadVault()
		env=NormalizeEnv(vault[account]["env"])
		PrintEnv(env)
		return
	
  	# _________________________________________
	if action=="lines-per-sec":
		N,T1,t1 = 0,time.time(),time.time()
		for line in sys.stdin:
			N+=1
			now=time.time()
			if (now-t1)>2.0:
				t1=now
				sec = now - T1
				print(f"Elapsed time={sec} lines={N:,} lps={N//sec}")
		return
 

  
# ////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	try:
		Main(sys.argv)
	except KeyboardInterrupt:
		pass
	sys.exit(0)