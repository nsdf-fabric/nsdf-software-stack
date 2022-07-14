#!/usr/bin/env python
# coding: utf-8
###edited by Naweiluo Zhou
import os, h5py, dxchange
import numpy as np
import imageio as io
from joblib import Parallel, delayed
import tomopy
import time ##
from mpi4py import MPI
NCORE =48  # Number of CPUs to assign to reconstruction.

# Where the data (.h5 files) are saved
#SRC = 'Scan Data'
SRC = '/home/cc/data'

# Where to save the reconstructed data:
RECON_DST = 'Reconstructions'  # Where to save the data
SLICE_RANGE = slice(900, 1000)  # slices to reconstruct ("Rows" from each projection)
SLICE_RANGE = slice(0, 2560)  # slices to reconstruct ("Rows" from each projection)

# Calculated center shift values for each file. Comment out files that you don't want to reconstruct.
center_shift_dict = {  
# Skip these files - no "white field" image in file: /////////////
##    "fly_scan_id_112437": 1280,
##    "fly_scan_id_112441": 1276,
##    "fly_scan_id_112443": 1274,
##    "fly_scan_id_112451": 1272,
##    "fly_scan_id_112453": 1280,
##    "fly_scan_id_112455": 1280,
##    "fly_scan_id_112458": 1278,
##    "fly_scan_id_112461": 1274,
##    "fly_scan_id_112464": 1276,
##    "fly_scan_id_112470": 1274,
##    "fly_scan_id_112475": 1272,
##    "fly_scan_id_112478": 1274,
##    "fly_scan_id_112482": 1274,
##    "fly_scan_id_112489": 1280,
##    "fly_scan_id_112491": 1272,
##    "fly_scan_id_112493": 1278,
##    "fly_scan_id_112495": 1278,
##    "fly_scan_id_112500": 1276,
##    "fly_scan_id_112502": 1273,
##    "fly_scan_id_112504": 1274,
    # "fly_scan_id_112507": ,  sample broken
    # "fly_scan_id_112508": ,  sample broken
    
# These scans are good!
    
    "fly_scan_id_112515_01": 1265,
    "fly_scan_id_112515_02": 1266,
    "fly_scan_id_112515_03": 1267,
    "fly_scan_id_112515_04": 1268,
    "fly_scan_id_112515_05": 1269,
    "fly_scan_id_112515_06": 1270,
#    "fly_scan_id_112515_07": 1271,
#    "fly_scan_id_112515_08": 1272,
#    "fly_scan_id_112515_09": 1273,

#    "fly_scan_id_112515_10": 1274,
########################################################################################################################
# you can do all these or just one
#    "fly_scan_id_112515_11": 1275,
 #   "fly_scan_id_112515_12": 1276,
  #  "fly_scan_id_112515_13": 1277,
   # "fly_scan_id_112515_14": 1278,
   # "fly_scan_id_112515_15": 1279,
   # "fly_scan_id_112515_16": 1280,
   # "fly_scan_id_112515_17": 1281,
   # "fly_scan_id_112515_18": 1281,
   # "fly_scan_id_112515_19": 1281,
   # "fly_scan_id_112515_20": 1281,
########################################################################################################################

    
#    "fly_scan_id_112517": 1265,
#    "fly_scan_id_112520": 1268,
#    "fly_scan_id_112522": 1268,
#    "fly_scan_id_112524": 1272,
#    "fly_scan_id_112526": 1268,
#    "fly_scan_id_112528": 1274,
#    "fly_scan_id_112530": 1266,
#    "fly_scan_id_112532": 1272,
    # "fly_scan_id_112534": , broken
    # "fly_scan_id_112535": 1282, # poor alignmnt
 #   "fly_scan_id_112537": 1270,
 #   "fly_scan_id_112540": 1264,
 #   "fly_scan_id_112542": 1266,
 #   "fly_scan_id_112543": 1260,
 #   "fly_scan_id_112545": 1260,
 #   "fly_scan_id_112548": 1260,
    }


def convert_to_8bit(img, vmin, vmax):
    """ Convert floating point data to an 8bit array """
    result = np.clip(img.astype(float) - vmin, 0, vmax-vmin) / (vmax - vmin) 
    return result * 255.0
def convert_to_16bit(img, vmin, vmax):
    """ Convert floating point data to a 16bit array """
    result = np.clip(img.astype(float) - vmin, 0, vmax-vmin) / (vmax - vmin) 
    return result * (2**16-1)
     
def recon_file(projections, theta, dpath, rot_center, mask=False, idx_start=0, **kwargs):
    """
    CPU-parallelized reconstruction using Tomopy. There's a strange bug where I cant use the built-in Tomopy parallelization, may be specific specifically to Windows?
    
    Inputs:
    + projections: array of shape (N_angles, N_rows, N_cols). The raw tomography data
    + theta: array of shape (N_angles,). The angles corresponding to each projection
    + dpath: where to save the data
    + mask: Float from (0.0 to 1.0) Radius of the circular mask applied to the  reconstructed data. 
    + rot_center: float. Location of the rotation axis (i.e., the corresponding column in the image data)
    + idx_start: integer, used to assign a unique name to each reconstructed slice.
    *** kwargs: dictionary of kwargs passed to "tomopy.recon". Commonly includes "algorithm"
    
    Output:
    * Saves the reconstructed 16bit slices to "dpath"
    """
    
    # Not the best practice, but makes sure there's a place to save the data
    if not os.path.isdir(dpath):
        os.makedirs(dpath)
        
    # # Select the appropriate algorithm to reconstruct the data with:
    if 'algorithm' not in kwargs.keys():
        algorithm = 'gridrec'
    else:
        algorithm = kwargs['algorithm']
        
    # Do a test reconstuction to figure out vmin, vmax to scale the reconstruction
    nradio, height, width = projections.shape
    proj_i = projections[:, ::20].reshape((nradio, -1, width))
    recon_test = tomopy.recon(proj_i, theta, center=rot_center, algorithm='gridrec', ncore=NCORE)
    vmin, vmax = np.percentile(
        recon_test[:, width//4:-width//4, width//4:-width//4], 
        (0.1, 99.9))

    # For use in parallelization: i = slice to reconstruct, idx = number to include in the saved file.
    def worker(i, idx):
        proj_i = projections[:, i].reshape((nradio, 1, width))
        # Perform an initial reconstrucition using "gridrec"
        recon_init = tomopy.recon(proj_i, theta, center=rot_center, algorithm='gridrec', ncore=NCORE)
        
        # If an iterative technique is used, then we can use the gridrect reconstruction as an initial value:
        if algorithm != 'gridrec':
            recon_i = tomopy.recon(proj_i, theta, center=rot_center, ncore=1,
                                   init_recon=recon_init,
                                   **kwargs)
        else: # just use the gridrec
            recon_i = recon_init
        
        # Convert to 16bit, apply circle mask, and save:
        recon_i = convert_to_16bit(recon_i, vmin, vmax)
        if mask:
            recon_i = tomopy.circ_mask(recon_i, 0, ratio=mask, ncore=1)
        io.imsave(os.path.join(dpath, '{:05d}.tif'.format(idx)),
            recon_i[0].astype('uint16'))
    
    Parallel(n_jobs=NCORE)(delayed(worker)(i, idx) for i, idx in enumerate(range(idx_start, idx_start+height)))
    


if __name__ == '__main__':
    # Do the reconstructions:
    comm=MPI.COMM_WORLD
    size = comm.Get_size()
    rank = comm.Get_rank()
    iter= len(center_shift_dict)
    if (size>iter):
        print("number of nodes should be no more than the len of the dict!!")
        os.abort()
    comm.barrier()   
   ###start multiple process (preferably the number of MPI processes=the len of the dictionary)
    for i in range (iter):
        if i%size!=rank:
            continue
        else:  

            
            file=list(center_shift_dict.keys())[i] #
            file1 = file[:-3]
            print('\t' + file , end='... ')
            print('\t' + file1, end='... ')
            #continue
            # Read in the .h5 file:
            with h5py.File(os.path.join(SRC, file1 + '.h5'), 'r') as container:
        
                # Extract the data
                theta = np.array(container['angle']) * np.pi / 180
                projections = container['img_tomo'][:, SLICE_RANGE]
                white = container['img_bkg_avg'][0, SLICE_RANGE]
                dark = container['img_dark_avg'][0, SLICE_RANGE]
            
                # Mask the obstructed projections. The load frame blocks the view in certain angles.
                # In brief, we find the indices where the image intensity is too low.
                idx_angle_filter = projections.shape[1]//2
                threshold = projections[:, idx_angle_filter].mean(axis=0)
                theta_filter = (projections[:, idx_angle_filter] > threshold).mean(axis=-1) > 0.5
                theta_slice = np.arange(theta.size, dtype='int')[theta_filter]
                theta_slice = slice(theta_slice.min(), theta_slice.max())
            
                theta = theta[theta_slice]
                projections = projections[theta_slice]

                # Normalize the projections:
                projections = tomopy.prep.normalize.normalize(projections, white, dark, ncore=NCORE)
                # Log transform the data:
                projections = tomopy.prep.normalize.minus_log(projections, ncore=NCORE)
                print(projections.shape)
        
                # Filter the data: Remove stripes, retrieve phase.
                projections = tomopy.prep.stripe.remove_stripe_fw(
                    projections, level=7, ncore=NCORE)
                projections = tomopy.prep.phase.retrieve_phase(
                    projections, pixel_size=0.01/100, dist=3, energy=7,
                    ncore=NCORE)
            
                # kwargs = {'algorithm': 'sirt', 'num_iter': 20}
                kwargs = {'algorithm': 'gridrec'}

                # Reconstruct, and save the data:              
               
                dpath = os.path.join(RECON_DST, os.path.splitext(file1)[0]+"_"+str(center_shift_dict[file])) ##NZ
                # if not os.path.isdir(dpath):
                #    os.makedirs(dpath)
                recon_file(projections, theta, dpath, center_shift_dict[file], mask=0.95, idx_start=SLICE_RANGE.start, 
                 **kwargs)
          
    comm.barrier()      
