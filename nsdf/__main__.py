import os,sys


# ////////////////////////////////////////////////////////////////////////
if __name__=="__main__":

	if "export-env" in sys.argv:
		"""
		python3 -m nsdf export-env s3-wasabi
		"""
		account=sys.argv[sys.argv.index( "export-env")+1]
		from nsdf.kernel import NormalizeEnv, PrintEnv, SetEnv, LoadVault
		vault=LoadVault()
		env=NormalizeEnv(vault[account]["env"])
		PrintEnv(env)
		sys.exit(0)
	
