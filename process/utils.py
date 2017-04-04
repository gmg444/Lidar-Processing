import requests
import subprocess as sb
import config as conf
import gdal, osr
import glob as gl

def exec_command_line(cmd):
    print (cmd)
    sb.call(cmd, shell=False)

def download_file(url, file_name):
    req = requests.get(url, stream=True)
    with open(file_name, 'wb') as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

gdal.AllRegister()

def write_tiff_file(dst_file, arr, x_min, y_min, no_data_value):
    driver = gdal.GetDriverByName('GTiff')
    rows, cols = arr.shape
    # Create new tiff file, write array to tiff file
    ds = driver.Create(dst_file, cols, rows, 1, gdal.GDT_Float32)
    band = ds.GetRasterBand(1)
    band.WriteArray(arr)
    band.SetNoDataValue(no_data_value)
    proj = osr.SpatialReference()
    proj.SetWellKnownGeogCS("EPSG:3857")
    ds.SetProjection(proj.ExportToWkt())
    geotrans = (x_min, 1, 0, y_min, 0, 1)
    # Set spatial reference and projection of output file to same as input file
    ds.SetGeoTransform(geotrans)
    ds.FlushCache()
    ds = None
    return dst_file

def convert_to_las(input_file, output_dir):
    # To thin, add this to command line:  -keep_every_nth 3
    # C:\Projects\lidar-data\pipeline\2513.las
    # las2las -i "C:\Projects\lidar-data\pipeline\2513.laz" -target_utm 19N -target_precision 0.01 -olaz
    # c:/LASTools/LASTools/bin/las2las -i "C:/Projects/lidar-data/pipeline/backup/2513.laz" -odir "C:/Projects/lidar-data/pipeline/" -olas -keep_z 10 2000-clip_to_bounding_box -keep_every_nth 2 -latlong -target_utm 18N -target_precision 0.01
    # To reproject, add this to command -target_utm 18N -target_precision 0.001
    # ~latlong -target_latlong
    cmd = conf.las_tools_dir + 'las2las -i "{0}" -odir "{1}" -olas -keep_z 10 2000 -clip_to_bounding_box'.format(input_file, output_dir)
    exec_command_line(cmd)
    return input_file.replace(".laz", ".las")

def create_point_cloud(input_file):
    output_file = input_file.replace(".txt", "")
    cmd = conf.saga_cmd_dir + "saga_cmd io_shapes 16 -POINTS={1} -FILE={0} -XFIELD=1 -YFIELD=2 -ZFIELD=3 -SKIP_HEADER=0 -FIELDSEP=1".format(input_file, output_file)
    exec_command_line(cmd)
    return output_file + ".spc"

def create_grid(input_file):
    output_file = input_file.replace(".spc", "")
    cmd = "saga_cmd pointcloud_tools 4 -POINTS={0} -OUTPUT=0 -GRID={1} -AGGREGATION=4 -CELLSIZE=1.000000".format(input_file, output_file)
    exec_command_line(cmd)
    return output_file + ".sdat"

def fill_grid_gaps(input_file):
    output_file = input_file.replace(".sdat", "_closed.sdat")
    cmd = "saga_cmd grid_tools 7 -INPUT={0} -RESULT={1} -THRESHOLD=0.100000".format(input_file, output_file)
    exec_command_line(cmd)
    return output_file

def add_srs_to_tiff(input_file, output_file, srid):
    # No data is -1 here
    cmd = conf.gdal_dir + "gdal_translate.exe -a_srs EPSG:{2} -a_nodata -1 {0} {1}".format(input_file, output_file, srid)
    exec_command_line(cmd)

def mosaic_tiles(wildcard_path, output_file, minx, miny, maxx, maxy):
    input_files = []
    for f_name in gl.glob(wildcard_path):
        # f_name_new = f_name.replace(".tif", "_3857.tif")
        # add_srs_to_tiff(f_name, f_name_new, 3857)
        input_files.append(f_name)
    tile_str = " ".join(input_files)
    # No data is -1 here - to  handle no data correctly, use add this command line:  -n -1
    # Problem is, this requires gdal_array, which is not provided with current version. see:
    # https://github.com/conda-forge/gdal-feedstock/issues/131
    cmd = 'C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal_merge.py" -ul_lr {0} {1} {2} {3} -a_nodata -1 -init -1 -n -1 -o {4} {5}'.format(minx, miny, maxx, maxy, output_file, tile_str)
    exec_command_line(cmd)
    return output_file

def create_output_tiles(mosaic, output_dir):
    # -a argument required, with 0,0,0 - see http://gis.stackexchange.com/questions/143818/osgeo4w-and-gdal-gdal2tiles-py-error
    # C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal2tiles.py" C:/Projects/lidar-data/NorthamptonMAMosaics/8_range_z_img_3857_mosaic.tif test -a 0,0,0 -p raster -x
    fill_gaps(mosaic)
    exported_file = mosaic.replace(".tif", "_hillshade.tif")
    hilshade(mosaic, exported_file) # -a 0,0,0
    cmd = 'C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal2tiles.py" {0} {1} -p raster '.format(exported_file, output_dir)
    exec_command_line(cmd)

def fill_gaps(input_file):
    # -a argument required, with 0,0,0 - see http://gis.stackexchange.com/questions/143818/osgeo4w-and-gdal-gdal2tiles-py-error
    cmd = 'C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal_fillnodata.py"-md 100 -si 2 -b 1 -nomask -of GTiff {0}'.format(input_file)
    exec_command_line(cmd)

def hilshade(input_file, output_file):
    cmd = conf.gdal_dir + "gdaldem hillshade -az 315 -z 1 {0} {1}".format(input_file, output_file)
    exec_command_line(cmd)
