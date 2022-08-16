import os,sys,time, shutil
from urllib.request import urlopen
from pprint import pprint

import numpy as np
import scipy
from   scipy import ndimage

import matplotlib.pyplot as plt

from PIL import Image 
import PIL 

import OpenVisus as ov

# //////////////////////////////////////////
def GetLogicSize(db):
	return [int(it) for it in db.getLogicSize()]

# //////////////////////////////////////////
def ReadSlab(db, Z1,Z2):
	# print(f"ReadSlab Z1={Z1} Z2={Z2}...")
	t1=time.time()
	width,height,depth=GetLogicSize(db)
	data=db.read(logic_box=[[0,0,Z1],[width,height,Z2]])
	print(f"ReadSlab Z1={Z1} Z2={Z2} done in {time.time()-t1:.2f} seconds, shape={data.shape} dtype={data.dtype} nbytes={data.nbytes} ({data.nbytes//1024**2}MB)")
	return data

# //////////////////////////////////////////
def WriteSlab(db, Z1,Z2, data, timestep):
	## print(f"WriteSlab Z1={Z1} Z2={Z2}...")
	t1=time.time()
	width,height,depth=GetLogicSize(db)
	db.write(data, logic_box=[[0,0,Z1],[width,height,Z2]],time=timestep)
	print(f"WriteSlab Z1={Z1} Z2={Z2} done in {time.time()-t1:.2f} seconds, shape={data.shape} dtype={data.dtype} nbytes={data.nbytes} ({data.nbytes//1024**2}MB)")
	return data


# /////////////////////////////////////////////////////////////////////////
def RotateAndShift(src, rotation=3.0,shift=(0,1,1)):

	t1=time.time()
	# print(f"RotateAndShift rotation={rotation} shift={shift}...") 

	if True:
		"""once shot slab version """

		dst=src

		if rotation:
			dst=scipy.ndimage.rotate(dst, rotation,axes=(1, 2), reshape=False) 

		if np.any(shift):
			dst=scipy.ndimage.shift(dst, shift)

	else:
		"""slice by slice version"""
		dst=np.copy(src)
		for Z in range(src.shape[0]):
			transformed=scipy.ndimage.rotate(
					src[Z,:,:], 
					rotation,
					axes=(1, 0), 
					reshape=False) 
			transformed=scipy.ndimage.shift(transformed, (shift[1],shift[2]))
			dst[Z,:,:] = transformed
	
	print(f"RotateAndShift rotation={rotation} shift={shift} done in {time.time()-t1:.2f} seconds")
	return dst
	


# /////////////////////////////////////////////////////////////////////////
def ShiftOnly(src, shift=(0,1,1)):

	t1=time.time()
	# print(f"ShiftOnly shift={shift}...") 

	width,height,depth=reversed(src.shape)

	x,y,z=reversed(shift)
	assert x>=0 and y>=0 and z==0

	dst=np.zeros(src.shape,src.dtype)
	dst[:,y:height,x:width]=src[:,0:height-y,0:width-x]

	print(f"ShiftOnly shift={shift} done in {time.time()-t1:.2f} seconds")
	return dst


# ///////////////////////////////////////////////////////
def TransformDataset(src, dst, timestep=0, rotation=0.0,shift=(0,0,0), slabs=None):
	
	assert slabs
	assert timestep>=0 
	assert len(slabs)==3 
	assert len(shift)==3 and shift[0]==0

	width,height,depth=GetLogicSize(src)

	if slabs[1]<0: 
		slabs=(slabs[0],depth,slabs[2])

	print("# *** TransformDataset","timestep",timestep,"rotation",rotation,"shift",shift, "slabs",slabs)

	for Z in range(slabs[0], slabs[1], slabs[2]) :
		z1=max(slabs[0],Z+0       )
		z2=min(slabs[1],Z+slabs[2])
		src_slab=ReadSlab(src, z1, z2)

		# too slow
		# dst_slab=RotateAndShift(src_slab,rotation=rotation, shift=shift)

		dst_slab=ShiftOnly(src_slab,shift=shift)
		WriteSlab(dst, z1, z2,dst_slab, timestep=timestep)

		# save_thumbnail (NOTE: i am saving only the extrema of the slam)
		# a=Image.fromarray(src_slab[ 0,:,:]);a.thumbnail((256,256), Image.ANTIALIAS);a.save(f"thumbnail.{z1+0:04d}.src.png")
		# b=Image.fromarray(dst_slab[ 0,:,:]);b.thumbnail((256,256), Image.ANTIALIAS);b.save(f"thumbnail.{z1+0:04d}.dst.png")
		# a=Image.fromarray(src_slab[-1,:,:]);a.thumbnail((256,256), Image.ANTIALIAS);a.save(f"thumbnail.src.{z2-1:04d}.png")
		# b=Image.fromarray(dst_slab[-1,:,:]);b.thumbnail((256,256), Image.ANTIALIAS);b.save(f"thumbnail.dst.{z2-1:04d}.png")

# ///////////////////////////////////////////////////////
def Main(args):

	import argparse
	parser = argparse.ArgumentParser(description="My script")
	
	parser.add_argument("--src","--source", type=str, help="source idx filename", required=True)
	parser.add_argument("--dst","--destination", type=str, help="destination", required=True) 
	parser.add_argument("--timestep", type=int, help="timestep", required=True) 
	parser.add_argument("--rotation", type=float, help="rotation", required=False, default=0) 
	parser.add_argument("--shift", type=str, help="shift", required=True) 
	parser.add_argument("--slabs", type=str, help="slabs==(z1,z2,slab_size)", required=True)

	args = parser.parse_args(args)
	print(args)

	args.shift=eval(args.shift)
	args.slabs=eval(args.slabs)
	
	src=ov.LoadDataset(args.src)
	dst=ov.LoadDataset(args.dst)
	TransformDataset(src, dst, timestep=args.timestep, rotation=args.rotation, shift=args.shift, slabs=args.slabs)


# ///////////////////////////////////////////////////////
if __name__=="__main__":
	Main(sys.argv[1:])
	sys.exit(0)
