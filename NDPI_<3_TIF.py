"""
Script to extract regions of interest (ROIs) from NDPI files and save them as TIF files.
ROIs are extracted by finding the contours in a binary image. 
The binary image is created using blurring and otsu thresholding. 
The user is prompted to select the channel from which the ROIs are extracted. 
The same ROIs are then used to crop the images from the other channels. 

Installation instructions can be found at the bottom of this script.

This is not the fastest script (single CPU).
It takes between 1-5 minutes per slide with 0.23-0.46um/pixel resolution. 
The user is prompted to select either resolution level.

"""

import openslide
import os
from PIL import ImageFilter
import cv2
import numpy as np


# ask for the path to the ndpis files
input_folder = input("Enter the path to the NDPI files: ")
# ask for the channel that contains the cropping template
CROPPING_TEMPLATE_CHANNEL_NAME = input("Enter the channel name that represents the cropping template: ")

# ask for the resolution level of the ndpi image
LEVEL = int(input("Enter the resolution level of the NDPI image (0 = highest resolution, 1 = second highest resolution): "))


# adjust THRESHOLD_SIZE to resolution level of ndpi image

if LEVEL == 0:
    THRESHOLD_SIZE = 10000000 # pixels squared, only keep rois that are larger than this threshold
elif LEVEL == 1:
    THRESHOLD_SIZE = 1000000 # pixels squared, only keep rois that are larger than this threshold

output_dir = input_folder + "/tif_files"

# make output directory if it does not exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)



ndpis_files = []
for file in os.listdir(input_folder):
    if file.endswith(".ndpis"):
        ndpis_files.append(file)

def get_ndpi_filenames(ndpis_file):
    ndpi_files = []
    with open(ndpis_file, 'r') as f:
        for line in f:
            if line.endswith('.ndpi\n'):
                # extract substring after "="
                line = line.split("=")[1]
                # save to list            
                ndpi_files.append(line.rstrip('\n'))
        # close file
        f.close()
    return ndpi_files


def ndpi_2_tif(ndpi_files):
    ndpi_image = openslide.open_slide(ndpi_files)
    # Convert the NDPI image of level 3 to a grayscale 8bit TIF image
    tiff_image = ndpi_image.read_region((0, 0), LEVEL, ndpi_image.level_dimensions[LEVEL]).convert('L')
    ndpi_image.close()
    return tiff_image 

def get_binary(tiff_image):
    # blur the image to remove noise
    blurred_image = tiff_image.filter(ImageFilter.GaussianBlur(25))

    # convert tiff_image to a binary image using otsu thresholding
    binary_image = blurred_image.point(lambda p: p > 0 and 255)

    # convert to numpy array
    binary_image = np.array(binary_image)

    return binary_image

def get_rois(ndpi_file):

    tiff_image = ndpi_2_tif(ndpi_files[0])
    # convert tiff_image to binary image
    binary_image = get_binary(tiff_image)
    
    # Find contours in binary image
    contours, hierarchy = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Get bounding rectangles of contours
    rois = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        rois.append((x, y, w, h))

    # calculate size of each roi
    sizes = []
    for roi in rois:
        sizes.append(roi[2] * roi[3])

    # only keep rois that are larger than THRSHOLD_SIZE
    rois = [roi for i, roi in enumerate(rois) if sizes[i] > THRESHOLD_SIZE]

    return rois




# loop over ndpis_files
for ndpis_file in ndpis_files:

    ndpi_files = get_ndpi_filenames(ndpis_file)
    # get the ndpi_file which has the CROPPING_TEMPLATE_CHANNEL_NAME in its name
    CROPPING_TEMPLATE_CHANNEL = [ndpi_file for ndpi_file in ndpi_files if CROPPING_TEMPLATE_CHANNEL_NAME in ndpi_file][0]
    # get rois from tiff image which is CROPPING_TEMPLATE_CHANNEL
    rois = get_rois(CROPPING_TEMPLATE_CHANNEL)
    # get number of rois
    number_of_rois = len(rois)

    # create for loop that iterates through ndpi files in input directory
    for ndpi_file in ndpi_files:
        if ndpi_file.endswith(".ndpi"):

            # create output filename based on input filename
            output_filename = os.path.join(output_dir, os.path.splitext(os.path.basename(ndpi_file))[0])
            
            # convert ndpi to tif
            tiff_image = ndpi_2_tif(ndpi_file)

            
            # crop each roi from the tiff image and save it using output_filename
            for i, roi in enumerate(rois):
                x, y, w, h = roi
                cropped_image = tiff_image.crop((x, y, x + w, y + h))
                # get roi number and dimensions of cropped image
                cropped_image_dimensions = cropped_image.size
                #print roi i of number_of_rois and dimensions of cropped_image and output_filename
                print("ROI %d of %d with dimensions %s saved as %s" % (i+1, number_of_rois, cropped_image_dimensions, output_filename + "_roi_0" + str(i) + ".tif"))
                cropped_image.save(output_filename + "_roi_0" + str(i) + ".tif")





"""

1) Installation (Ubuntu)

1.1) Install OpenSlide

sudo apt install openslide-tools

1.2) Install fast package manager Mamba

curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh

1.3) Other operating systems (Windows, Mac OS)

https://openslide.org/api/python/#installing
https://github.com/conda-forge/miniforge 


2) Create Mamba environment and install dependencies

mamba create -n openslide-env openslide-python opencv-python 


3) Usage

In CLI, type

mamba activate openslide-env
python NDPI2TIF.py

"""
