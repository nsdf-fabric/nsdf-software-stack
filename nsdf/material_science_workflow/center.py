
import tomopy
from tomopy import downsample
import os, h5py
import numpy as np
import time
import skimage.restoration as skr
import skimage
import scipy.ndimage.filters as snf
from scipy.ndimage import filters
import dxchange
from pathlib import Path
import gc, sys, tifffile
import imageio as io
from matplotlib import pyplot as plt
import scipy.ndimage as ndi
from joblib import Parallel, delayed

"""
A wrong center shift value create wrong alignment and can give errors like double boundaries. 
Maybe we can try the tomopy' s built in approach "rot_center = tomopy.recon.rotation.find_center(tomo, theta, init=1265, tol=0.5, mask=True, ratio=1.0, sinogram_order=False)". 
However I didn't had much luck with this when I used it.

We have a manual approach to estimate the center shift value, where print the center slice for various rotation center values and decide by going through those slices. 
Maybe Brendan can give help with you understanding the entire process.
 Included in the attachments is a copy of center shift estimation jupyter notebook.
"""

def convert_to_8bit(img, vmin, vmax):
    result = np.clip(img.astype(float) - vmin, 0, vmax-vmin) / (vmax - vmin) 
    return result * 255.0

def write_center(projections, white, dark, theta, dpath, center_shift_candidates, mask=False, algorithm='gridrec'):
    """ Do trial reconstructions to find the center shift. 
    Inputs:
       Projections, theta = see tomopy documentation.
       dpath = filepath string. Where to save the results.
       center_shift_candidates = list of integers that define each candidate value. The value is "offset from the middle of the image", such that a value of "-1" is one pixel from the image center.
    """
    if not os.path.isdir(dpath):
        os.makedirs(dpath)
        
    for ii in range(0,np.size(center_shift_candidates)):
        rot_center = (projections.shape[-1] / 2) + center_shift_candidates[ii]
        projections_norm = tomopy.normalize(projections, white_avg, dark_avg) 
        projections_norm = projections_norm - np.min(projections_norm) + 0.0000001
        projections_neglog = tomopy.prep.normalize.minus_log(projections_norm)
        recon = tomopy.recon(projections_neglog, theta, center=rot_center, algorithm=algorithm)
    
        if mask:  # Add a circular mask
            recon = tomopy.circ_mask(recon, 0, ratio=mask)
        
        recon = recon[0]
        vmin, vmax = np.percentile(recon, (0.02, 99.99))
        recon = convert_to_8bit(recon, vmin, vmax)
        
        try:
            io.imsave(os.path.join(dpath, '{:04.1f}.tiff'.format(rot_center)),
                      recon)
        except FileNotFoundError:
            os.makedirs(dpath)
            io.imsave(os.path.join(dpath, '{:04.1f}.tiff'.format(rot_center)),
                      recon)


if __name__=="__main__":

	# Read the radiographs, flat-field & dark-field images from the h5 file
	SRC_path = 'Scan Data'
	file = 'fly_scan_id_112515'
	Data = h5py.File(os.path.join(SRC_path, file + '.h5'), 'r')

	Slice_Range = slice(945,947)
	# Load the White Field images
	white = Data['img_bkg'][:,Slice_Range]
	white_avg = Data['img_bkg_avg'][0,Slice_Range]

	# Load the Dark Field Images
	dark = Data['img_dark'][:,Slice_Range]
	dark_avg = Data['img_dark_avg'][0,Slice_Range]

	# Load the Projections/Radiographs
	projections = Data['img_tomo'][:,Slice_Range]

	# Load the Angle Information
	theta = np.array(Data['angle']) * np.pi / 180

	dpath = './Center_Shift/'
	center_shift_candidates = np.arange(-50, 50, 0.5)
	write_center(projections, white_avg, dark_avg, theta, os.path.join(dpath, file), center_shift_candidates)