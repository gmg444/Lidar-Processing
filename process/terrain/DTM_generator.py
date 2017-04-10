import subprocess as sb
# import xmltodict
# import requests
# import config as conf

# 1. save .las files into .txt files (fields: X(coordinates), Y(coordinates), Z(coordinates), I(tensity), c(lassification))
def las_to_txt(input_file):
    output_file = input_file.replact(".las", "")
    cmd = "las2txt -i {0} -o {1} --parse xyzic".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file + ".txt"

# 2. create saga point clouds (Module Name: "Import Point Cloud from Text File")
def create_point_cloud(input_file):
    output_file = input_file.replace(".txt", ".spc")
    cmd = "saga_cmd io_shapes 16 -POINTS={1} -FILE={0} -FIELDS='4;5' -FIELDNAMES='intensity;classification' -FIELDTYPES="2;2" -FIELDSEP=2".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file

# 3. extract ground points (Module Name: "Point Cloud Reclassifier / Subset Extractor") (-ATTRIB(field)='classification'; -MODE(get subclass)=1; -OLD=2; -SOPERATOR=2(<=))
def ground_points(input_file):
    output_file = input_file.replace(".spc", "_class2.spc")
    cmd = "saga_cmd pointcloud_tools 6 -INPUT={0} -ATTRIB='classification' -RESULT={1} -MODE=1 -OLD=2 -SOPERATOR=2".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file

# 4. create grid for point cloud (Module Name: "Point Cloud to Grid") -OUTPUT=0 only z; -AGGREGATION=3 lowest z
def create_grid(input_file):
    output_file = input_file.replace(".spc", "")
    cmd = "saga_cmd pointcloud_tools 4 -POINTS={0} -OUTPUT=0 -GRID={1} -AGGREGATION=3 -CELLSIZE=1.000000".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file + ".sgrd"

# 5. remove non-ground cells (Module Name: "DTM Filter (slope-based)") -RADIUS=10; -TERRAINSLOPE=75
def DTM_filter(input_file):
    output_file = input_file.replace("_class2.sgrd", "_ground.sgrd")
    cmd = "saga_cmd grid_filter 7 -INPUT={0} -RADIUS=10 -TERRAINSLOPE=75 -STDDEV -GROUND={1}".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file

# 6. close gaps (Module Name: "Close Gaps") (requires .sgrd files as inputs)
def fill_grid_gaps(input_file):
    output_file = input_file.replace("_ground.sgrd", "_DTM.sgrd")
    cmd = "saga_cmd grid_tools 7 -INPUT={0} -RESULT={1} -THRESHOLD=0.100000".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file

# 7. interpolation of a DTM surface (Module Name: "Multilevel B-Spline Interpolation (from Grid)")
# *** The interpolated image isn't clear: 1. The grid may have changed 2. The parameter is different from GUI***
#def interpolation(input_file):
#    output_file = input_file.replace(".sgrd", "_interpolated.sgrd")
#    cmd = "saga_cmd grid_spline 5 -GRIDPOINTS={0} -USER_GRID={1}".format(input_file, output_file)
#    sb.call(cmd, shell=False)
#    return output_file

# 8. smoothing the DTM (Module Name: "Multi Direction Lee Filter")
# *** There is no significant change after running this step ***
#def smoothing_DTM(input_file):
#    output_file = input_file.replace(".sgrd", "_smoothed.sgrd")
#    cmd = "saga_cmd grid_filter 3 -INPUT={0} -RESULT={1} -NOISE_REL=2 -WEIGHTED".format(input_file, output_file)
#    sb.call(cmd, shell=False)
#    return output_file

# 7. calculating slope & aspect (Module Name: "Slope, Aspect, Curvature") (This step generates both slope & aspect from DTM)
def slope_aspect(input_file):
    output_file1 = input_file.replace("_DTM.sgrd", "_slope.sgrd")
    output_file2 = input_file.replace("_DTM.sgrd", "_aspect.sgrd")
    cmd = "saga_cmd ta_morphometry 0 -ELEVATION={0} -SLOPE={1} -ASPECT={2}".format(input_file, output_file1, output_file2)
    sb.call(cmd, shell=False)
    return output_file

# 8. export .tif files
def export_tif(slope_grid, aspect_grid):
    output_slope_tif = slope_grid.replace(".sgrd", ".tif")
    output_aspect_tif = aspect_grid.replace(".sgrd", ".tif")
    # -COL_PALETTE=9 yellow & red
    cmd = "saga_cmd io_grid_image 0 -GRID={0} -FILE={1} -COL_PALETTE=9".format(slope_grid, output_slope_tif)
    sb.call(cmd, shell=False)
    # -COL_PALETTE=6 white & red
    cmd = "saga_cmd io_grid_image 0 -GRID={0} -FILE={1} -COL_PALETTE=6".format(aspect_grid, output_aspect_tif)
    sb.call(cmd, shell=False)
    return output_slope_tif, output_aspect_tif

# 9. generate tile files
def tile_generator(slope_tif, aspect_tif):
    output_slope_tile = slope_tif.replace(".tif", "_tiles")
    output_aspect_tile = aspect_tif.replace(".tif", "_tiles")
    # -z 0-5 (zoom level 0-5), -w none (disable HTML output)
    cmd = "gdal2tiles.py -p raster -z 0-5 -w none {0}".format(slope_tif)
    sb.call(cmd, shell=False)
    cmd = "gdal2tiles.py -p raster -z 0-5 -w none {0}".format(aspect_tif)
    sb.call(cmd, shell=False)
    return output_slope_tile, output_aspect_tile
