import gdal
import os
import ogr
import numpy as np

gdal.AllRegister()

# #######################################################
# set PATH=C:\Python34_64;C:\Python34_64\Scripts;%PATH%
# set PYTHONPATHC=:\Python34_64;%PYTHONPATH%

def process_file(input_file):
    (fileRoot, fileExt) = os.path.splitext(input_file)
    outFileName = fileRoot + "_mod" + fileExt
    ds = gdal.Open(input_file)
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    bands = ds.RasterCount
    tree_band = ds.GetRasterBand(1)
    myarray = np.array(ds.GetRasterBand(1).ReadAsArray())
    print ("Numpy array attributes", myarray.shape, myarray.max(), myarray.min(), myarray.mean())

process_file('C:/Projects/lidar-data/20150429_QL1_18TXM690687_NE_range_z_float_3857.tif')
