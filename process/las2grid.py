# ##############################################################################
# Code to use laspy to load data into pandas and numpy arrays, to get grid values
# more efficiently, without any point-by-point iteration.
# ##############################################################################
import numpy as np
import laspy as ls
import pandas as pd
import math
import subprocess as sb
import scipy.ndimage as ndi
import config as conf
import utils as steps
import tif2tree as tft
import tif2terrain as tfterr
import scipy.ndimage as ndi

""""
Be sure laspy folder is in the current directory

Execute these commands at the command line:
set CONDA_FORCE_32BIT=
conda create -n py27 python=2.7
activate py27
pip install numpy
pip install pandas

In pycharm, selecct the py27 virtual environment as the project interpreter
When running from the command-line, type activate ph27 before running
"""
# saga_cmd ta_lighting 2 -GRD_DEM=./20150514_QL1_18TXM691687_NW_dsm.tif -GRD_DIRECT=out_direct.tif -GRD_DIFFUS=out_diffus.tif -GRD_TOTAL=out_total.tif -HOUR_RANGE_MIN=5.000000 -HOUR_RANGE_MAX=20.000000 -METHOD=2
def generate_grids(input_file):
    no_data_value = -1

    # Read in las file with laspy
    f = ls.file.File(input_file, mode="rw")
    X = (f.X * f.header.scale[0]) + f.header.offset[0]
    Y = (f.Y * f.header.scale[1]) + f.header.offset[1]

    # Projection from https://gist.github.com/springmeyer/871897, vectorized with numpy
    if conf.is_amherst:
        x = X/3.28084
        y = Y/3.28084
    else:
        x = (X * 20037508.34 / 180.0)
        y = (np.log(np.tan((90.0 + Y) * math.pi / 360.0)) / (math.pi / 180.0) * 20037508.34 / 180.0)
    z = (f.Z * f.header.scale[2])

    # Create int array for indexing grid x, y
    x_int = np.floor(x + 0.5).astype(np.int32)
    y_int = np.floor(y + 0.5).astype(np.int32)

    # Convert to range starting with zero
    x_int = x_int - x_int.min()
    y_int = y_int - y_int.min()

    # Create xyz numpy arrays from points array, where z is elevation, classification, intensity,
    # return number, and number of returns.
    xyz = np.vstack([x_int, y_int, z]).transpose().astype(np.int32)
    xyc = np.vstack([x_int, y_int, f.classification]).transpose().astype(np.int32)
    xyi = np.vstack([x_int, y_int, f.intensity]).transpose().astype(np.int32)
    # Todo - change minz to last returns only; maxz to be first returns only.

    # Create a pandas dataframe to make it easier to slice and dice the arrays. Max, min, range z.
    df = pd.DataFrame(xyz)
    df.columns = ['x', 'y', 'z']
    max_z = df.groupby(['x', 'y'], sort=False).max()
    min_z = df.groupby(['x', 'y'], sort=False).min()
    range_z = max_z - min_z

    # Create numpy array for gridded output, and set it to no_data_value. Existing are x/y combinations
    # where points exists.
    arr = np.zeros((y_int.max()+1, x_int.max()+1))
    existing_x = [rt[0] for rt in max_z.index]
    existing_y = [rt[1] for rt in max_z.index]

    # Output max z
    arr[:, :] = no_data_value
    arr[existing_y, existing_x] = max_z.z.values
    dsm_file = input_file.replace(".las", "_dsm.tif")
    new_file = steps.write_tiff_file(dsm_file, arr, x.min(), y.min(), no_data_value)
    # tfs.tif_to_solar(dsm_file, dsm_file.replace(".tif", "_solar.tif"))
    dsm_arr = arr + 0

    # Output min z
    arr[:, :] = no_data_value
    arr[existing_y, existing_x] = min_z.z.values
    min_z_arr = arr + 0

    # Output range z
    arr[:,:] = no_data_value
    arr[existing_y, existing_x] = range_z.z.values
    height_tif = input_file.replace(".las", "_height.tif")
    new_file = steps.write_tiff_file(height_tif, arr, x.min(), y.min(), no_data_value)
    range_z_arr = arr + 0

    trees_arr = tft.make_tree_shp(height_tif, height_tif.replace("_height.tif", "_trees.shp"))

    # Clean up - seems to help reduce memory usage a bit
    max_z = None
    min_z = None
    range_z = None
    df = None

    # Classification
    df = pd.DataFrame(xyc)
    df.columns = ['x', 'y', 'z']
    max_c = df.groupby(['x', 'y'], sort=False).max()

    # Output classification
    arr[:,:] = no_data_value
    arr[existing_y, existing_x] = max_c.z.values
    # new_file = steps.write_tiff_file(input_file.replace(".las", "_class.tif"), arr, x.min(), y.min(), no_data_value)
    class_arr = arr + 0

    ground_cells = ((class_arr == 2) * (range_z_arr == 0)).astype(np.int32)
    ground_arr = min_z_arr * ground_cells
    ground_arr[ground_arr <= 0] = -1

    new_file = steps.write_tiff_file(input_file.replace(".las", "_dem_temp.tif"), ground_arr, x.min(), y.min(), no_data_value)
    dem_file = new_file.replace("_dem_temp.tif", "_dem.tif")
    # -a argument required, with 0,0,0 - see http://gis.stackexchange.com/questions/143818/osgeo4w-and-gdal-gdal2tiles-py-error
    cmd = 'C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal_fillnodata.py" -md 100 -b 1 -of GTiff {0} {1}'.format(new_file, dem_file)
    sb.call(cmd, shell=False)

    # buildings_cells = (class_arr == 1).astype(np.int32)
    # struct = ndi.generate_binary_structure(2, 1)
    # # Expand out buildings cells to catch buildings edges
    # # buildings_cells = ndi.binary_dilation(buildings_cells, structure=struct, iterations=2)
    # ground_cells[buildings_cells==1] = 1
    # # Expand ground cells to catch power lines
    # ground_cells = ndi.binary_dilation(ground_cells, iterations=2)
    # tree_cells = np.logical_not (ground_cells)
    # tree_cells[range_z_arr < 5] = False
    # tree_cells[range_z_arr > 50] = False
    # # Expand back out tree
    # tree_cells = ndi.binary_dilation(tree_cells, structure=struct, iterations=2)
    # tree_arr = 1.0 * tree_cells
    # new_file = steps.write_tiff_file(input_file.replace(".las", "_trees.tif"), tree_arr, x.min(), y.min(), no_data_value)

    # Clean up
    max_c = None
    df = None
    class_arr = None
    # range_z_arr = None
    min_z_arr = None
    ground_mask = None
    grond_arr = None

    # Intensity
    df = pd.DataFrame(xyi)
    df.columns = ['x', 'y', 'z']
    mean_i = df.groupby(['x', 'y'], sort=False).mean()

    # Output intensity
    arr[:,:] = no_data_value
    arr[existing_y, existing_x] = mean_i.z.values
    # new_file = steps.write_tiff_file(input_file.replace(".las", "_intensity.tif"), arr, x.min(), y.min(), no_data_value)

    tfterr.make(dem_file, trees_arr, arr, dsm_arr, range_z_arr)

    # Clean up
    max_i = None

# For debugging - you can display gridded numpy arrays in matplotlib:
# pip install matplotlib
# import matplotlib.pyplot as plt
# plt.imshow(arr)

if __name__ == "__main__":
    # Single test file:
    output_files = generate_grids("C:/Projects/lidar-data/test_file/20150429_QL1_18TXM690689_SW_1.las")