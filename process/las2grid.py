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
import utils
import glob as gl
import os
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
        x = X
        y = Y
    else:
        x = (X * 20037508.34 / 180.0)
        y = (np.log(np.tan((90.0 + Y) * math.pi / 360.0)) / (math.pi / 180.0) * 20037508.34 / 180.0)

    z = (f.Z * f.header.scale[2])
    arr_filter = (z < np.percentile(z, 98)) * (z > np.percentile(z, 2))
    x_min = x.min()
    y_min = y.min()
    x = x - x.min()
    y = y - y.min()
    if conf.is_amherst:
        x /= 3.28084
        y /= 3.28084
        z /= 3.28084

    # Create int array for indexing grid x, y
    x_int = np.floor(x + 0.5).astype(np.int32)
    y_int = np.floor(y + 0.5).astype(np.int32)
    x *= arr_filter
    y *= arr_filter
    z *= arr_filter

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
    dsm_file = input_file.replace(".las", "_dsm_temp.tif")
    new_file = steps.write_tiff_file(dsm_file, arr, x_min, y_min, no_data_value)
    dsm_file = new_file.replace("_dsm_temp.tif", "_dsm.tif")
    # -a argument required, with 0,0,0 - see http://gis.stackexchange.com/questions/143818/osgeo4w-and-gdal-gdal2tiles-py-error
    cmd = 'C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal_fillnodata.py" -md 100 -b 1 -of GTiff {0} {1}'.format(new_file, dsm_file)
    utils.exec_command_line(cmd)

    # tfs.tif_to_solar(dsm_file, dsm_file.replace(".tif", "_solar.tif"))
    dsm_arr = arr + 0

    # Output min z
    arr[:, :] = no_data_value
    arr[existing_y, existing_x] = min_z.z.values
    minz_arr = arr + 0
    minz_arr[minz_arr <= 0] = -1
    minz_file = input_file.replace(".las", "_minz_temp.tif")
    new_file = steps.write_tiff_file(minz_file, minz_arr, x_min, y_min, no_data_value)
    minz_file = new_file.replace("_minz_temp.tif", "_minz.tif")
    # -a argument required, with 0,0,0 - see http://gis.stackexchange.com/questions/143818/osgeo4w-and-gdal-gdal2tiles-py-error
    cmd = 'C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal_fillnodata.py" -md 100 -b 1 -of GTiff {0} {1}'.format(new_file, minz_file)
    utils.exec_command_line(cmd)

    # Output range z
    arr[:,:] = no_data_value
    arr[existing_y, existing_x] = range_z.z.values
    range_z_arr = arr + 0

    # Clean up - seems to help reduce memory usage a bit
    # max_z = None
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
    # new_file = steps.write_tiff_file(input_file.replace(".las", "_class.tif"), arr, x_min, y_min, no_data_value)
    class_arr = arr + 0

    ground_cells = ((class_arr == 2) * (range_z_arr == 0)).astype(np.int32)
    ground_arr = minz_arr * ground_cells
    ground_arr[ground_arr <= 0] = -1

    new_file = steps.write_tiff_file(input_file.replace(".las", "_dem_temp.tif"), ground_arr, x_min, y_min,  no_data_value)
    dem_file = new_file.replace("_dem_temp.tif", "_dem.tif")
    # -a argument required, with 0,0,0 - see http://gis.stackexchange.com/questions/143818/osgeo4w-and-gdal-gdal2tiles-py-error
    cmd = 'C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal_fillnodata.py" -md 100 -b 1 -of GTiff {0} {1}'.format(new_file, dem_file)
    utils.exec_command_line(cmd)

    # range_z_arr = None
    # dem_arr = utils.tif2numpy(dem_file)
    dsm_arr = utils.tif2numpy(dsm_file)
    minz_arr = utils.tif2numpy(minz_file)
    range_z_arr = dsm_arr - minz_arr
    # range_z_arr = dsm_arr - dem_arr
    height_tif = input_file.replace(".las", "_height.tif")
    new_file = steps.write_tiff_file(height_tif, range_z_arr, x_min, y_min, no_data_value)
    trees_arr = tft.make_tree_shp(height_tif, height_tif.replace("_height.tif", "_trees.shp"))
    tree_pct = ((trees_arr > 0).sum() / float(trees_arr.shape[0] * trees_arr.shape[1])) * 100.0
    tree_area = (trees_arr > 0).sum()
    all_area = float(trees_arr.shape[0] * trees_arr.shape[1])
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
    # new_file = steps.write_tiff_file(input_file.replace(".las", "_trees.tif"), tree_arr, x_min, y_min, no_data_value)

    # Clean up
    max_c = None
    df = None
    class_arr = None
    # range_z_arr = None
    minz_arr = None
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

    with open(input_file.replace(".las", ".txt"), "w") as f:
        mz = dsm_arr[dsm_arr > 1].min()
        for r in range(dsm_arr.shape[0]):
            for c in range(dsm_arr.shape[1]):
                if dsm_arr[r, c] > 1:
                    f.write("{0} {1} {2:.2f} {3:.2f}\n".format(c - float(dsm_arr.shape[1])/2.0, r - float(dsm_arr.shape[0])/2.0, dsm_arr[r, c] - mz, arr[r, c]))

    # Clean up
    arr = None
    dsm_arr = None
    dem_arr = None
    max_i = None

    return tree_pct, tree_area, all_area

# For debugging - you can display gridded numpy arrays in matplotlib:
# pip install matplotlib
# import matplotlib.pyplot as plt
# plt.imshow(arr)

if __name__ == "__main__":
    # Single test file:
    # output_files = generate_grids("C:/Projects/lidar-data/test_file/20150429_QL1_18TXM690689_SW_1.las")
    # fnames = ["170_mosaic_dsm.tif", "168_mosaic_dsm.tif", "161_mosaic_dsm.tif", "154_mosaic_dsm.tif", "151_mosaic_dsm.tif"]
    dir_name = "C:/Projects/LIDAR-PROCESSING/Lidar-Processing/site/output/"
    for file_name in gl.glob("D:/lidar-maps-data/amherst/*dsm.tif"):
        dsm_arr = utils.tif2numpy(file_name)
        with open(dir_name + "1000_" + os.path.basename(file_name).replace(".tif", ".txt"), "w") as f:
            for r in range(dsm_arr.shape[0]):
                for c in range(dsm_arr.shape[1]):
                    f.write("{0} {1} {2}\n".format(c - float(dsm_arr.shape[1])/2.0, r - float(dsm_arr.shape[0])/2.0, dsm_arr[r, c]))
    print "all done"
    # np.savetxt('D:/lidar-maps-data/test_point_cloud.txt', dsm_arr, delimiter=' ', newline='\n')
