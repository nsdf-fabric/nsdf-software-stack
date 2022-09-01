import os, itertools

import h5py
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import colors
import pandas as pd 
# using datetime module
import datetime
import imageio as io
  
from tensorflow import keras
#from keras import layers, callbacks, models, optimizers, utils, metrics, preprocessing
from tensorflow.keras import backend as K

def get_msd_model(img_shape, n_layers=50, kernels_per_layer=2):
    
    dilation_range = [1, 2, 4, 6, 8]
    kernel_size=(3,3)
    
    input_shape = list(img_shape)
    
    # assemble the model
    inp = keras.layers.Input(shape=input_shape)
    
    # 1x1 convolution to extract a (N,N,1) image for the residual network
    shortcut = keras.layers.Conv2D(1, (1,1), activation='linear')(inp)

    # Concatenate a series of dilated Conv2D filters:
    x = inp
    for i, dilation in zip(range(n_layers), itertools.cycle(dilation_range)):
        # Do the convolution / activation / bn:
        x_i = keras.layers.Conv2D(
                kernels_per_layer, kernel_size, padding='same',
                dilation_rate=(dilation, dilation)
            )(x)
        x_i = keras.layers.Activation('relu')(x_i)
        x_i = keras.layers.BatchNormalization()(x_i)
        
        # Append to the stack:
        x = keras.layers.Concatenate(axis=-1)([x, x_i])
    
    output = keras.layers.Conv2D(1, kernel_size=(1,1), activation='sigmoid')(x)

    model = keras.Model(inp, output)
    return model


def load_and_reshape_model(model_fpath, new_img_shape=(2560, 2560, 1)):
    saved_model = keras.models.load_model(model_fpath)

    # Build a blank model with a new input shape, then update weights.
    new_model = get_msd_model(
        new_img_shape
    )
    
    # Update the weights.
    for i in range(len(saved_model.layers)):
        new_model.layers[i].set_weights(saved_model.layers[i].get_weights())
    
    return new_model

def normalize_crop_reshape_image(fpath):
    crop = slice(250, 2250), slice(250, 2250)
    img = io.imread(fpath)[crop].astype(float)
    vmin, vmax = np.percentile(img, (0.01, 99.9))
    img = np.clip(img - vmin, 0, vmax-vmin) / (vmax - vmin)
    return img

def process_whole_image(src, dst, fname):
    """
    Read an image from os.path.join(src, fname), apply
    CNN, and save to os.path.join(dst, fname)
    """
    img = normalize_crop_reshape_image(os.path.join(src, fname))
    img_seg = np.expand_dims(img, (0, 3))
    img_segment = new_model.predict(img_seg)
    img_norm = (np.squeeze(img_segment)*255).astype('uint8')
    outpath = os.path.join(dst, fname)
    try:
        io.imsave(outpath,img_norm) #sp.resize(np.squeeze(img_norm),[2000,2000]))
    except FileNotFoundError:
        os.makedirs(dst)
        io.imsave(outpath,img_norm) #sp.resize(np.squeeze(img_norm),[2000,2000]))
    return img_norm

def process_all_images_in_folder(src, dst):
    file_list = os.listdir(src)
    for file in file_list:
        print(file)
        process_whole_image(src, dst, file)

##### Main Script #####
##### Creating a new CNN Model to run for the whole image at once  #####
modelfilepath = '/Segmentation/CNN Model/trained_models/seg_msd_50_2_ep100'
new_model = load_and_reshape_model(modelfilepath,new_img_shape=(None,None,1))
new_model.compile(optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy'])

# Where the reconstructed slices are saved:
src = '/fly_scan_id_112517/Reconstructions/'
# Where to save the processed images:
dst = '/fly_scan_id_112517/SegResCPUVersion/'

img_segment = process_all_images_in_folder(src, dst)
