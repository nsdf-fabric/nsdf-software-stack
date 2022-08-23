
import os,sys
from .main import Main
  
# ////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
	try:
		Main(sys.argv[0:])
	except KeyboardInterrupt:
		pass
	sys.exit(0)