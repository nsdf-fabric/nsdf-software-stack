import os,time,glob,math,sys,shutil,shlex,subprocess,datetime,argparse,zlib,glob,struct
from multiprocessing.pool import ThreadPool

import OpenVisus as ov

from nsdf.kernel import logger, S3, S3Sync, FileExists, TouchFile, SafeReplaceFile,rmdir

# ////////////////////////////////////////////////////////////////////////////////////////
"""

  IDX File format

  FileHeader == Uint32[10]== all zeros (not used)

  class BlockHeader
  {
    Uint32  prefix_0    = 0; //not used
    Uint32  prefix_1    = 0; 
    Uint32  offset_low  = 0;
    Uint32  offset_high = 0;
    Uint32  size        = 0;
    Uint32  flags       = 0;
    Uint32  suffix_0    = 0; //not used
    Uint32  suffix_1    = 0; //not used
    Uint32  suffix_2    = 0; //not used
    Uint32  suffix_3    = 0; //not used
	};

  enum
  {
    NoCompression = 0,
    ZipCompression = 0x03,
    JpgCompression = 0x04,
    //ExrCompression =0x05,
    PngCompression = 0x06,
    Lz4Compression = 0x07,
    ZfpCompression = 0x08,    
    CompressionMask = 0x0f
  };

  enum
  {
    FormatRowMajor = 0x10
  };
"""

# ////////////////////////////////////////////////////////////////////////////////////////
def NormalizeArcoArg(value):
	
	"""
	Example: modvisus | 0 | 1mb | 512kb
	"""

	if value is None or value=="modvisus":
		return 0
	
	if isinstance(value,str):
		return ov.StringUtils.getByteSizeFromString(value)  
	
	assert(isinstance(value,int))
	return int(value)

# ////////////////////////////////////////////////////////////////////////////////////////
def NormalizeCompressionArg(value):

	"""
	Example:
		{
			'algorithm':'zip',
			'level':-1,
			'num-threads':16
		}
		|
		'zip'
		|
		None
	"""

	if value is None:
		return None

	if isinstance(value,str):
		if value[0]=='{':
			value=eval(value)
		else:
			value={'algorithm':value}

	assert(isinstance(value,dict))
	return {
		"algorithm": value.get("algorithm","zip"),
		"num-threads": value.get("num-threads",16),
		"level": value.get("level",-1)
	}



# ////////////////////////////////////////////////////////////////////////
def NormalizeImageStackArgument(value):

	if isinstance(value,str) and value[0]=="{":
		value=eval(value)

	elif isinstance(value,str):
		value={"local":value}

	assert isinstance(value,dict)
	assert "local" in value
	value["remote"]=value.get("remote",None)
	value["keep-local"]=value.get("keep-local",True)	

	# they are pattern
	assert value["remote"] is None or  "/**/" in value["remote"]
	assert                              "/**/" in value["local"]

	return value

# ////////////////////////////////////////////////////////////////////////
def NormalizeDbArgument(value):

	if isinstance(value,str) and value[0]=="{":
		value=eval(value)

	elif isinstance(value,str):
		value={"local":value}

	assert isinstance(value,dict)
	assert "local" in value
	value["remote"]=value.get("remote",None)
	value["keep-local"]=value.get("keep-local",True)
	value["arco"]=NormalizeArcoArg(value.get("arco","modvisus"))

	assert value["local"][0]=='/'                      # absolute path
	assert os.path.splitext(value["local"])[1]==".idx" # extension must be idx

	return value



# ////////////////////////////////////////////////////////////////////////////////////////
def CompressLocalArcoDataset(idx_filename:str="", filename_pattern:str="",compression={"algorithm":"zip","level":-1,"num-threads":16}):

	compression=NormalizeCompressionArg(compression)

	if not compression:
		return

	T1=time.time()
	UNCOMPRESSED_SIZE,COMPRESSED_SIZE=0,0
	def CompressFile(filename):
		nonlocal UNCOMPRESSED_SIZE,COMPRESSED_SIZE
		with open(filename,"rb") as f: mem=f.read()	
		UNCOMPRESSED_SIZE+=len(mem)
		mem=zlib.compress(mem,level=compression["level"]) # https://docs.python.org/3/library/zlib.html#zlib.compress
		COMPRESSED_SIZE+=len(mem)
		SafeReplaceFile(filename, mem)
		del mem
	p=ThreadPool(compression["num-threads"])
	p.map(CompressFile, glob.glob(filename_pattern,recursive=True))
	RATIO=int(100*COMPRESSED_SIZE/UNCOMPRESSED_SIZE)
	logger.info(f"CompressLocalArcoDataset all done in {time.time()-T1} seconds {RATIO}%")


# ////////////////////////////////////////////////////////////////////////////////////////
def UncompressLocalArcoDataset(idx_filename:str="", filename_pattern:str="",compression={"algorithm":"raw","level":-1,"num-threads":16}):

	"""
	make sure all the files are compressed
	"""

	compression=NormalizeCompressionArg(compression)

	if not compression:
		return

	T1=time.time()

	UNCOMPRESSED_SIZE,COMPRESSED_SIZE=0,0

	def UncompressFile(filename):
		nonlocal UNCOMPRESSED_SIZE,COMPRESSED_SIZE
		with open(filename,"rb") as f: mem=f.read()	
		COMPRESSED_SIZE+=len(mem)
		mem=zlib.decompress(mem) 
		UNCOMPRESSED_SIZE+=len(mem)
		SafeFileReplace(filename, mem)
		del mem

	p=ThreadPool(compression["num-threads"])
	p.map(UncompressFile, glob.glob(filename_pattern,recursive=True))
	RATIO=int(100*COMPRESSED_SIZE/UNCOMPRESSED_SIZE)
	logger.info(f"UncompressLocalArcoDataset all done in {time.time()-T1} seconds {RATIO}%")


# ////////////////////////////////////////////////////////////////////////////////////////
def CompressLocalModVisusDataset(idx_filename:str="",filename_pattern:str="",compression={"algorithm":"zip","level":-1,"num-threads":16},verbose=False):

	compression=NormalizeCompressionArg(compression)

	# i can decide to uncompress a db
	#if not compression:
	#	return

	T1=time.time()
	FULL_SIZE,COMPRESSED_SIZE=0,0
	CompressionMask, ZipMask=0x0f,0x03
	idx=ov.IdxFile()
	idx.load(idx_filename)
	# logger.infoidx.toString())
	blocks_per_file=idx.blocksperfile
	filename_template=idx.filename_template
	assert filename_template[0]=="."
	bin_dir=os.path.abspath(os.path.join(os.path.dirname(idx_filename),filename_template))
	bin_dir=os.path.abspath(bin_dir.split("%")[0]+"**/*.bin")
	num_fields=idx.fields.size()
	file_header_size=10*4
	block_header_size=10*4
	tot_blocks=blocks_per_file*num_fields
	header_size=file_header_size+block_header_size*tot_blocks

	for filename in glob.glob(filename_pattern,recursive=True):

		t1=time.time()
		with open(filename,"rb") as f:
			mem=f.read()

		# read the header
		v=[struct.unpack('>I',mem[cur:cur+4])[0] for cur in range(0,header_size,4)]; assert(len(v)% 10==0)
		v=[v[I:I+10] for I in range(0,len(v),10)]
		file_header  =v[0]
		block_headers=v[1:]
		assert file_header==[0]*10
		full_size=header_size

		def CompressBlock(B):
			block_header=block_headers[B]
			field_index=B // blocks_per_file
			blocksize=idx.fields[field_index].dtype.getByteSize(2**idx.bitsperblock)
			assert block_header[0]==0 and block_header[1]==0 and block_header[6]==0 and block_header[7]==0 and block_header[8]==0 and block_header[9]==0
			offset=(block_header[2]<<0)+(block_header[3]<<32)
			size  =block_header[4]
			flags =block_header[5]
			block=mem[offset:offset+size]
			flags_compression=flags & CompressionMask
			if flags_compression == ZipMask:
				decompressed=zlib.decompress(block)
			else:
				assert(flags_compression==0)
				decompressed=block
			assert len(decompressed)==blocksize
			nonlocal full_size
			full_size+=blocksize

			if compression and compression["algorithm"]=="zip":
				compressed=zlib.compress(decompressed,level=compression["level"]) # https://docs.python.org/3/library/zlib.html#zlib.compress
			else:
				compressed=decompressed # uncompress

			return (B,compressed)

		# compress blocks in parallel
		p=ThreadPool(compression.get("num-threads",16))
		COMPRESSED=p.map(CompressBlock, range(tot_blocks))
		COMPRESSED=sorted(COMPRESSED, key=lambda tup: tup[0])

		compressed_size=header_size+sum([len(it[1]) for it in COMPRESSED])
		mem=bytearray(mem[0:compressed_size])

		# write file header
		mem[0:40]=struct.pack('>IIIIIIIIII',0,0,0,0,0,0,0,0,0,0)

		# fill out new mem
		offset=header_size
		for I in range(tot_blocks):
			compressed=COMPRESSED[I][1]
			size=len(compressed)
			# block header
			header_offset=file_header_size+I*40
			mem[header_offset:header_offset+40]=struct.pack('>IIIIIIIIII',0,0,(offset & 0xffffffff),(offset>>32),size,(block_headers[I][5] & ~CompressionMask) | ZipMask,0,0,0,0)
			mem[offset:offset+size]=compressed; offset+=size
		assert offset==compressed_size

		SafeReplaceFile(filename, mem)
		del mem

		ratio=int(100*compressed_size/full_size)
		FULL_SIZE+=full_size
		COMPRESSED_SIZE+=compressed_size

		if verbose:
			logger.info(f"Compressed {filename}  in {time.time()-t1} ratio({ratio}%)")

	RATIO=int(100*COMPRESSED_SIZE/FULL_SIZE)
	logger.info(f"CompressLocalModVisusDataset all done in {time.time()-T1} seconds {RATIO}%")

# ////////////////////////////////////////////////////////////////////////////////////////
def CompressDataset(
	idx_filename:str=None,
	filename_pattern:str=None,
	arco=None,
	compression={"algorithm":"zip","level":-1,"num-threads":16}):

	arco=NormalizeArcoArg(arco)
	if arco:
		return CompressLocalArcoDataset(idx_filename,filename_pattern,compression)
	else:
		return CompressLocalModVisusDataset(idx_filename,filename_pattern,compression)
		

# ////////////////////////////////////////////////////////////////////////////////////////
def CreateLocalAccess(db, arco="modvisus"):

	arco=NormalizeArcoArg(arco)
	if not arco:
		return db.createAccessForBlockQuery()
	else:
		# NOTE: Dataset will create a DiskAccess for (arco) IdxFIle but the default is to set compression to zip, instead here I am disabling compression in general
		ret = db.createAccessForBlockQuery(ov.StringTree.fromString(f"<access type='DiskAccess' compression='raw' />"))
		ret.disableWriteLock()
		return ret

# ////////////////////////////////////////////////////////////////////////////
def ConvertLocalImageStack(
		image_file_pattern:str=None, 
		idx_filename:str=None,
		arco="modvisus",
		verbose=False
	):

	# must be local use absolute paths
	assert image_file_pattern[0]=='/' 
	assert idx_filename[0]=='/' 

	assert os.path.splitext(idx_filename)[1]==".idx"

	arco=NormalizeArcoArg(arco)

	# get filenames
	if True:
		objects=sorted(glob.glob(image_file_pattern,recursive=True))
		tot_slices=len(objects)
		logger.info(f"ConvertLocalImageStack tot_slices {tot_slices} image_file_pattern={image_file_pattern}...")
		if tot_slices==0:
			error_msg=f"Cannot find images inside {image_file_pattern}"
			logger.info(error_msg)
			raise Exception(error_msg)	

	# guess 3d volume size and dtype
	if True:
		import imageio
		first=imageio.imread(objects[0]) # the first image it's needed for the shape and dtype
		depth=tot_slices
		height=first.shape[0]
		width=first.shape[1]
		nchannels=first.shape[2] if len(first.shape)>=3 else 1
		dtype=f'{first.dtype}[{nchannels}]'
	
	# this is the field
	field=ov.Field('data',dtype,'row_major')

	# one-file==one-block (NOTE: arco is the maximum blocksize, it will be less for power-of-two block aligment, for example in case of RGB data)
	# for example arco=1mb, samplesperblock=256k blocksize=256*3=756kb<1mb
	if arco:
		bitsperblock = int(math.log2(arco // field.dtype.getByteSize())) 
	else:
		bitsperblock=16

	samples_per_block=2**bitsperblock
	blocksize=field.dtype.getByteSize(samples_per_block)

	def Generator():
		import imageio
		for I,filename in enumerate(objects): 
			if verbose:
				logger.info(f"{I}/{tot_slices} Reading image file {filename}")
			yield imageio.imread(filename)

	generator=Generator()

	db=ov.CreateIdx(
		url=idx_filename, 
		dims=[width,height,depth],
		fields=[field],
		bitsperblock=bitsperblock,
		arco=arco)

	assert(db.getMaxResolution()>=bitsperblock)
	access=CreateLocalAccess(db, arco=arco)
	db.writeSlabs(generator, access=access)

# ////////////////////////////////////////////////////////////////////////
def ConvertImageStack(
	creates: str=None, 
	src={'remote':'','local':'','keep-local':True}, 
	dst={'local':'','remote':'','keep-local':True, 'arco':'modvisus'}, 
	compression={"algorithm":"zip", "level":-1, "num-threads":16}):

	T1=time.time()
	logger.info(f"ConvertImageStack src={src} dst={dst} creates={creates}...")

	# for rehentrant calls
	if creates and FileExists(creates):
		logger.info(f"skipping since {creates} already exists")
		return

	src=NormalizeImageStackArgument(src)
	dst=NormalizeDbArgument(dst)
	compression=NormalizeCompressionArg(compression)

	# sync with remote source
	if src["remote"]:
		S3Sync(logger, f"cloud-to-local",src["remote"], src["local"])

	# convert
	if True:
		t1=time.time()
		ConvertLocalImageStack(
			image_file_pattern=src["local"],
			idx_filename=dst["local"],
			arco=dst["arco"],
			verbose=False)
		sec=time.time()-t1
		logger.info(f"convert-image-stack image_dir={src['local']} idx_filename={dst['local']} arco={dst['arco']} done in {sec} seconds")


	# remove local source (src[local] includes the pattern)
	if not src["keep-local"]:
		rmdir(src["local"].split("**")[0])

	# compress
	if compression:

		"""
		NOTE: OLD way to compress
			   python3 -m OpenVisus compress-dataset --compression zip --dataset {dst['local']}
			   find /path/to/bin/files -type f -name '*.bin' -exec bash -c 'pigz --force --zlib {}' \;
		"""

		CompressDataset(
			idx_filename=dst['local'],
			filename_pattern=f"{os.path.dirname(dst['local'])}/**/*.bin",
			compression=compression,
			arco=dst["arco"])

	# sync with remote destination
	if dst["remote"]:
		S3Sync(logger, f"local-to-cloud", os.path.dirname(dst['local']),os.path.dirname(dst['remote'])) 

	# remove IDX (dst[local] is the idxfilename)
	if not dst["keep-local"]:
		rmdir(os.path.dirname(dst["local"]))

	# remember I did the convertion
	if creates:
		TouchFile(creates)

	SEC=time.time()-t1
	logger.info(f"ConvertImageStack src={src} dst={dst} creates={creates} all DONE in {SEC} seconds")
	return True


# ////////////////////////////////////////////////////////////////////////////
def CopyDataset(
	creates:str=None,
	src={'remote':'', 'local':'', 'keep-local':True, 'arco': 'modvisus'}, 
	dst={'local':'' ,'remote':'', 'keep-local':True, 'arco': 'modvisus'},
	compression={"algorithm":"zip", "level":-1, "num-threads":16},
	verbose=True):

	T1=time.time()

	# for rehentrant calls
	if creates and FileExists(creates):
		logger.info(f"skipping since {creates} already exists")
		return

	src=NormalizeDbArgument(src)
	dst-NormalizeDbArgument(dst())
	compression=NormalizeCompressionArg(compression)

	# sync with remote source
	if src["remote"]:
		S3Sync(logger, f"cloud-to-local",src["remote"], src["local"])

	SRC=ov.LoadIdxDataset(src["local"])
	
	Dfields=[]
	for Sfield in SRC.getFields():
		Sfield=SRC.getField(Sfield)
		Dfields.append(ov.Field(Sfield.name,Sfield.dtype,'row_major'))

	# todo: multiple fields, but I have the problem of fields with different dtype will lead to different bitsperblock, how to solve?
	if dst["arco"]:
		assert len(SRC.getFields())==1
		Dbitsperblock = int(math.log2(dst["arco"] // Dfields[0].dtype.getByteSize())) 
	else:
		Dbitsperblock=16

	# todo other cases
	timesteps=SRC.getTimesteps().asVector()
	assert len(timesteps)==1

	dims=[int(it) for it in SRC.getLogicSize()]

	DST=ov.CreateIdx(
		url=dst["local"], 
		dims=dims,
		fields=Dfields,
		bitsperblock=Dbitsperblock,
		arco=dst["arco"])

	assert(DST.getMaxResolution()>=Dbitsperblock)

	Saccess=CreateLocalAccess(SRC, src["arco"]) 
	Daccess=CreateLocalAccess(DST, dst["arco"])  # NOTE: first write uncompressed (!)

	pdim=SRC.getPointDim()
	assert pdim==2 or pdim==3 # TODO other cases

	piece=[1024,1024,1] if pdim==2 else [512,512,512]
	W=dims[0]
	H=dims[1]
	D=dims[2] if pdim==3 else 1

	Saccess.beginRead()
	Daccess.beginWrite()
	
	for timestep in timesteps:
		for fieldname in SRC.getFields():
			Sfield=SRC.getField(fieldname)
			Dfield=DST.getField(fieldname)
			for z1 in range(0,W,piece[2]):
				for y1 in range(0,H,piece[1]):
					for x1 in range(0,D,piece[0]):
						t1=time.time()
						x2=min(x1+piece[0],W)
						y2=min(y1+piece[1],H)
						z2=min(z1+piece[2],D) 
						logic_box=ov.BoxNi(ov.PointNi(x1,y1,z1),ov.PointNi(x2,y2,z2))
						logic_box.setPointDim(pdim)
						data=SRC.read( logic_box=logic_box,time=timestep,field=Sfield,access=Saccess)
						DST.write(data,logic_box=logic_box,time=timestep,field=Dfield,access=Daccess)
						if verbose:
							sec=time.time()-t1
							logger.info(f"Wrote {logic_box.toString()} time({timestep}) field({Sfield.name}) in {sec} seconds")

	Saccess.endRead()
	Daccess.endWrite()

	# remove local source (src[local] is the idx filename)
	if not src["keep-local"]:
		rmdir(os.path.dirname(src["local"]))

	# compress
	if compression:
		CompressDataset(
			idx_filename=dst["local"],
			filename_pattern=f"{os.path.dirname(dst['local'])}/**/*.bin",
			arco=dst["arco"],
			compression=compression)

	# sync with remote destination
	if dst["remote"]:
		S3Sync(logger, f"local-to-cloud", os.path.dirname(dst['local']),os.path.dirname(dst['remote'])) 

	# remove local destination (dst[local] is the idx filename)
	if not dst["keep-local"]: 
		rmdir( os.path.dirname(dst['local']))

	# remember I did the convertion
	if creates:
		TouchFile(creates)

	SEC=time.time()-T1
	logger.info(f"CopyDataset src={src} dst={dst} done in {SEC} seconds")



# ////////////////////////////////////////////////////////////////////
def Main(args):

	action=args[1]

	# ____________________________________________________________________
	if action=="convert-image-stack":

		"""
	Piline
	src["remote"] --->|aws-s3-sync|---> src["local"] ---> dst["local"]--->|aws-s3-sync|---> dst["remote"]

EXAMPLES:

# [OK] example `modvisus`
python3 -m nsdf.convert convert-image-stack \
   --src "{'remote':'s3://Pania_2021Q3_in_situ_data/test/image_stack/**/*.png','local':'/tmp/image-stack/**/*.png','keep-local':True}" \
   --dst "{'local':'/mnt/d/GoogleSci/visus_dataset/arco/cat/modvisus/visus.idx','arco':'modvisus'}" 

# [OK] example of `arco/1mb` 
python3 -m nsdf.convert convert-image-stack \
  --src "{'remote':'s3://Pania_2021Q3_in_situ_data/test/image_stack/**/*.png','local':'/mnt/d/GoogleSci/visus_dataset/arco/cat/image-stack/**/*.png' ,'keep-local':True}" \
  --dst "{'local':'/mnt/d/GoogleSci/visus_dataset/arco/cat/1mb/visus.idx','remote':None, 'keep-local':True, 'arco':'1mb'}"
		"""

		parser = argparse.ArgumentParser(description=action)
		parser.add_argument('--creates',type=str,required=False,default=None) 
		parser.add_argument('--src',type=str,required=True,default=None)
		parser.add_argument('--dst',type=str,required=True,default=None)  
		parser.add_argument('--compression',type=str,required=False,default="zip")
		args=parser.parse_args(args[2:])

		ConvertImageStack(
			creates=args.creates,
			src=args.src, 
			dst=args.dst,
			compression=args.compression
		)

	# ____________________________________________________________________
	elif action=="copy-dataset":

		"""
	Pipeline
	src["remote"] --->|aws-s3-sync|---> src["local"] -> dst["local"] --->|aws-s3-sync|---> dst["remote"]

EXAMPLES:

# [OK] copy `modvisus`->`modvisus` dataset
python3 -m nsdf.convert copy-dataset \
   --src "{'local':'/mnt/d/GoogleSci/visus_dataset/arco/cat/modvisus/visus.idx',     'arco':'modvisus'}" \
   --dst "{'local':'/mnt/d/GoogleSci/visus_dataset/arco/cat/modvisus-bis/visus.idx', 'arco':'modvisus'}" \
   --compression "{'algorithm':'zip','level':-1,'num-threads':16}" \
   --verbose 

# [OK] copy `modvisus`->`arco` dataset
python3 -m nsdf.convert copy-dataset \
   --src "{'local':'/mnt/d/GoogleSci/visus_dataset/arco/cat/modvisus/visus.idx',      'arco':'modvisus'}" \
   --dst "{'local':'/mnt/d/GoogleSci/visus_dataset/arco/cat/modvisus-arco/visus.idx', 'arco':'1mb'}" \
   --compression "{'algorithm':'zip','level':-1,'num-threads':16}" \
   --verbose 

python3 -m nsdf.convert copy-dataset \
   --src "{'local':'/mnt/d/GoogleSci/visus_dataset/2kbit1/zip/hzorder/visus.idx',  'arco':'modvisus'}" \
   --dst "{'local':'/mnt/d/GoogleSci/visus_dataset/arco/2kbit1/1mb/visus.idx',     'arco':'1mb'}" \
   --compression "{'algorithm':'zip','level':-1,'num-threads':16}" \
   --verbose 
		"""

		parser = argparse.ArgumentParser(description=action)
		parser.add_argument('--creates',type=str,required=False,default=None) 
		parser.add_argument('--src',type=str,required=True,default=None) 
		parser.add_argument('--dst',type=str,required=True,default=None)
		parser.add_argument('--compression',type=str,required=False,default=None)
		parser.add_argument('--verbose',required=False,action='store_true')
		args=parser.parse_args(args[2:])

		CopyDataset(
			creates=args.creates,	
			src=args.src,
			dst=args.dst,
			compression=args.compression,	
			verbose=args.verbose
		)

	# ____________________________________________________________________
	elif action=="compress-dataset":

		"""
EXAMPLES:

# [OK] compress `modvisus` dataset (NOTE: to UNCOMPRESS just use ` --compression "raw"`)
python3 -m nsdf.convert compress-dataset \
   --idx-filename      /mnt/d/GoogleSci/visus_dataset/arco/cat/modvisus/visus.idx \
   --filename-pattern "/mnt/d/GoogleSci/visus_dataset/arco/cat/modvisus/visus/**/*.bin" \
   --arco "modvisus" \
   --compression "{'algorithm':'zip','level':-1,'num-threads':16}"

# [TO-TEST] compress `arco 1mb` dataset (NOTE: you MUST be sure you didn't compress the arco files already)
python3 -m nsdf.convert compress-dataset \
   --idx-filename      /mnt/d/GoogleSci/visus_dataset/arco/cat/1mb/visus.idx \
   --filename-pattern "/mnt/d/GoogleSci/visus_dataset/arco/cat/1mb/visus/**/*.bin" \
   --arco "1mb" \
   --compression "{'algorithm':'zip','level':-1,'num-threads':16}"
		"""

		parser = argparse.ArgumentParser(description=action)
		parser.add_argument('--idx-filename',type=str,required=True,default=None) 
		parser.add_argument('--filename-pattern',type=str,required=True,default=None)
		parser.add_argument('--arco',type=str,required=False,default="modbisus")
		parser.add_argument('--compression',type=str,required=False,default=None)
		args=parser.parse_args(args[2:])

		CompressDataset(
			idx_filename=args.idx_filename,
			filename_pattern=args.filename_pattern,
			arco=args.arco,
			compression=args.compression,)

	else:
		raise Exception(f"unknown {action}")

