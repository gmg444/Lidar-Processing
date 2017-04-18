import scipy.ndimage as ndi
import numpy as np
import ogr
import gdal
import config as conf
import glob as gl
import utils as ut
import matplotlib.pyplot as plt

def make(dem_file, trees_arr, intensity_arr, dsm_arr, height_arr):
    # Apply gaussian filter to make dem and contours less jagged
    ds = gdal.Open(dem_file, gdal.GA_Update)
    #Assign variables to information needed tp create output
    band = ds.GetRasterBand(1)
    geotrans = ds.GetGeoTransform()
    proj = ds.GetProjection()
    dem_arr = band.ReadAsArray()
    dem_arr = ndi.gaussian_filter(dem_arr, 5)
    ds.GetRasterBand(1).WriteArray(dem_arr)
    ds.FlushCache()
    ds = None

    # Try to identify buildings
    buildings_arr = dsm_arr - dem_arr
    buildings_arr[buildings_arr < 3] = 0
    buildings_arr[trees_arr > 0] = 0
    buildings_arr[buildings_arr > 0] = 1
    buildings_arr[height_arr > 3] = 0
    # other_array = np.zeros(buildings_arr.shape)
    # other_array[buildings_arr < 1] = 1
    # other_array = ndi.binary_dilation(other_array, iterations=2)
    # buildings_arr *= np.invert(other_array)
    buildings_arr = ndi.binary_dilation(buildings_arr, iterations=2)

    # Save buildings tiff
    dest_file = dem_file.replace("_dem.tif", "_bldgs.tif")
    driver = gdal.GetDriverByName('GTiff')
    #Create new tiff file, write array to tiff file
    dataset = driver.Create(dest_file, buildings_arr.shape[1], buildings_arr.shape[0], 1, gdal.GDT_Byte)
    dataset.GetRasterBand(1).WriteArray(buildings_arr)
    #Set spatial reference and projection of output file to same as input file
    dataset.SetGeoTransform(geotrans)
    dataset.SetProjection(proj)
    dataset.FlushCache()
    dataset = None

    # Convert to shape file
    in_shp = ut.make_polygon(dest_file, dest_file.replace(".tif", ".shp"), "buildings")
    ut.dissolve_polygon(in_shp, in_shp)

    # Detect impervious surface
    impervious_arr = np.ones(buildings_arr.shape)
    impervious_arr[intensity_arr > 10000] = 0
    impervious_arr[intensity_arr < 0] = 0
    impervious_arr[buildings_arr > 0] = 0
    impervious_arr[trees_arr > 0] = 0
    impervious_arr[height_arr > 1] = 0
    impervious_arr = ndi.binary_dilation(impervious_arr, iterations=2)

    # Output as tiff
    dest_file = dem_file.replace("_dem.tif", "_impervious.tif")
    driver = gdal.GetDriverByName('GTiff')
    #Create new tiff file, write array to tiff file
    dataset = driver.Create(dest_file, impervious_arr.shape[1], impervious_arr.shape[0], 1, gdal.GDT_Byte)
    dataset.GetRasterBand(1).WriteArray(impervious_arr)
    #Set spatial reference and projection of output file to same as input file
    dataset.SetGeoTransform(geotrans)
    dataset.SetProjection(proj)
    dataset.FlushCache()
    dataset = None

    # Convert to shape file
    in_shp = ut.make_polygon(dest_file, dest_file.replace(".tif", ".shp"), "impervious surfaces")
    ut.dissolve_polygon(in_shp, in_shp)

