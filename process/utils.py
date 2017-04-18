import requests
import subprocess as sb
import config as conf
import gdal, osr
import glob as gl
import ogr
import gdal
import pandas as pd
import geopandas as gpd
from shapely.wkt import loads

def exec_command_line(cmd, shell_flag=False):
    print (cmd)
    sb.call(cmd, shell=shell_flag)

def download_file(url, file_name):
    print ("Downloading", url)
    req = requests.get(url, stream=True)
    with open(file_name, 'wb') as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

gdal.AllRegister()

def write_tiff_file(dst_file, arr, x_min, y_min, no_data_value):
    print ("Writing tiff file", dst_file)
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
    print ("Converting to LAS", input_file)
    cmd = conf.las_tools_dir + 'las2las -i "{0}" -odir "{1}" -olas -keep_z 10 2000 -clip_to_bounding_box'.format(input_file, output_dir)
    exec_command_line(cmd)
    return input_file.replace(".laz", ".las")

def create_point_cloud(input_file):
    print ("Create point cloud", input_file)
    output_file = input_file.replace(".txt", "")
    cmd = conf.saga_cmd_dir + "saga_cmd io_shapes 16 -POINTS={1} -FILE={0} -XFIELD=1 -YFIELD=2 -ZFIELD=3 -SKIP_HEADER=0 -FIELDSEP=1".format(input_file, output_file)
    exec_command_line(cmd)
    return output_file + ".spc"

def create_grid(input_file):
    print ("Create grid", input_file)
    output_file = input_file.replace(".spc", "")
    cmd = "saga_cmd pointcloud_tools 4 -POINTS={0} -OUTPUT=0 -GRID={1} -AGGREGATION=4 -CELLSIZE=1.000000".format(input_file, output_file)
    exec_command_line(cmd)
    return output_file + ".sdat"

def fill_grid_gaps(input_file):
    print ("Fill grid gaps", input_file)
    output_file = input_file.replace(".sdat", "_closed.sdat")
    cmd = "saga_cmd grid_tools 7 -INPUT={0} -RESULT={1} -THRESHOLD=0.100000".format(input_file, output_file)
    exec_command_line(cmd)
    return output_file

def add_srs_to_tiff(input_file, output_file, srid):
    # No data is -1 here
    print ("Adding srs to tiff", input_file)
    cmd = conf.gdal_dir + "gdal_translate.exe -a_srs EPSG:{2} -a_nodata -1 {0} {1}".format(input_file, output_file, srid)
    exec_command_line(cmd)

def mosaic_tiles(wildcard_path, output_file, minx, miny, maxx, maxy):
    print ("Mosaicking tiles", wildcard_path)
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
    print ("Outputting tiles")
    fill_gaps(mosaic)
    exported_file = mosaic.replace(".tif", "_hillshade.tif")
    hilshade(mosaic, exported_file) # -a 0,0,0
    cmd = 'C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal2tiles.py" {0} {1} -p raster '.format(exported_file, output_dir)
    exec_command_line(cmd)

def fill_gaps(input_file):
    print ("Filling gaps")
    # -a argument required, with 0,0,0 - see http://gis.stackexchange.com/questions/143818/osgeo4w-and-gdal-gdal2tiles-py-error
    cmd = 'C:/Anaconda2/python.exe "C:/Program Files/GDAL/gdal_fillnodata.py"-md 100 -si 2 -b 1 -nomask -of GTiff {0}'.format(input_file)
    exec_command_line(cmd)

def hilshade(input_file, output_file):
    print ("Hillshading")
    cmd = conf.gdal_dir + "gdaldem hillshade -az 315 -z 1 {0} {1}".format(input_file, output_file)
    exec_command_line(cmd)

def make_polygon(infile, outfile, name):
    print ("Make polygon", infile)
    #input tif file
    ds = gdal.Open(infile)
    tree_band = ds.GetRasterBand(1)
    polylayer = name
    drv = ogr.GetDriverByName("ESRI Shapefile")
    dst_ds = drv.CreateDataSource(outfile)
    dst_layer = dst_ds.CreateLayer(polylayer, srs=None)
    #Create New Field in output shapefile to assign value to
    newField = ogr.FieldDefn('Value', ogr.OFTInteger)
    dst_layer.CreateField(newField)
    gdal.Polygonize(tree_band, None, dst_layer, 0, [], callback=None)
    return outfile

def dissolve_polygon(infile, outfile):
    print ("Dissolve polygons", infile)
    tree_layer = gpd.read_file(infile)
    tree_layer = tree_layer[tree_layer.Value == 1]
    tree_subset = tree_layer[['geometry', 'Value']]
    # dissolve polygons by Value
    dissolved_tree_subset = tree_subset.dissolve(by='Value')
    # dissolved_tree_subset.plot()
    # head = dissolved_tree_subset.head()
    dissolved_tree_subset.to_file(outfile)
    return outfile

def merge_tiles(wildcard_path, output_file, clip_poly, remove_smaller_than=0):
    print ("Merge tiles", wildcard_path)
    files = gl.glob(wildcard_path)
    layers = []
    for f in files:
        layers.append(gpd.read_file(f))
    poly = gpd.GeoDataFrame(pd.concat(layers, ignore_index=True))
    if remove_smaller_than > 0:
        poly = poly[poly.geometry.area > remove_smaller_than]
    poly.crs = {'init': 'epsg:3857'}
    poly.geometry = poly.geometry.buffer(5)
    dissolved = poly.dissolve(by='FID')
    dissolved.geometry = dissolved.geometry.buffer(-5)
    dissolved.crs = {'init': 'epsg:3857'}
    dissolved = dissolved.to_crs({'init' :'epsg:4326'})
    # This is the main output shape file
    dissolved.to_file(output_file)

def dissolve_polygon(infile, outfile):
    print ("Dissolve polygons", infile)
    layer = gpd.read_file(infile )
    layer = layer[layer.Value == 1]
    layer = layer[['geometry','Value']]
    #dissolve polygons by Value
    dissolved = layer.dissolve(by='Value')
    # dissolved_tree_subset.plot()
    # head = dissolved_tree_subset.head()
    dissolved.to_file(outfile)
    return outfile

def save_clip_poly(wkt, clip_file):
    print ("Get clip poly", wkt)
    pgon = loads(wkt)
    df = gpd.GeoDataFrame([{"Value": 1, "geometry": pgon}], index=[1])
    df.crs = {'init' :'epsg:4326'}
    df.to_file(clip_file)

def contours(input_file, output_file, clip_poly):
    print ("Contours", input_file)
    cmd = conf.gdal_dir + 'gdal_contour -a "elevation" -i 5.0 {0} {1}'.format(input_file, output_file)
    exec_command_line(cmd)
    poly = gpd.GeoDataFrame.from_file(output_file)
    poly.crs = {'init': 'epsg:3857'}
    poly = poly.to_crs({'init' :'epsg:4326'})
    poly.to_file(output_file)  # , driver="GeoJSON")

def save_to_shp(poly, out_file):
    print ("Save to shp")
    poly = poly.to_crs({'init': 'epsg:3857'})
    poly.to_file(out_file)
    # Clip shape file - note last param is input.
    # ogr2ogr -clipsrc northampton.shp test_out.shp mosaic_contours.shp
    # Convert to simplified geojson - note last param is input.
    # ogr2ogr -f GeoJSON -simplify 0.00001 mosaic_contours_simplified.json mosaic_contours.shp
    # Converts to topojson
    # geo2topo tracts=mosaic_contours_simplified.json > mosaic_contours_simplified.topojson
    # Quantize file to get rid of meaningless precision
    # topoquantize 1e6 -o quantized.json mosaic_contours_simplified.topojson

def finalize(merged_file, clip_poly):
    print ("Finalize", merged_file)
    clipped_file = merged_file.replace(".shp", "_clip.shp")
    # Clip to selected area
    cmd = "ogr2ogr -clipsrc {0} {1} {2}".format(clip_poly, clipped_file, merged_file)
    exec_command_line(cmd)
    # Convert to simplified geojson.
    geo_json_file = merged_file.replace(".shp", ".json")
    cmd = "ogr2ogr -f GeoJSON -simplify 0.00001 {0} {1}".format(geo_json_file, clipped_file)
    exec_command_line(cmd)
    # Converts to topojson
    topo_json_file = merged_file.replace(".shp", ".topojson")
    cmd = "geo2topo tracts={0} > {1}".format(geo_json_file, topo_json_file)
    # Shell has to be true for node commands to work
    exec_command_line(cmd, True)
    # Quantize file to get rid of meaningless precision
    quantized_file = merged_file.replace(".shp", "_quantized.topojson")
    cmd  = "topoquantize 1e6 -o {0} {1}".format(quantized_file, topo_json_file)
    exec_command_line(cmd, True)

