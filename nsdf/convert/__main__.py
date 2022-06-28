import os,sys

# ////////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	from nsdf.kernel import  SetupLogger
	
	import logging
	os.makedirs("/tmp/nsdf",exist_ok=True)
	SetupLogger(logger, level=logging.INFO, handlers=[
		logging.StreamHandler(),
		logging.FileHandler( "/tmp/nsdf/nsdf.log")])

	from nsdf.convert import Main
	Main(sys.argv)

	


	