import subprocess as sb
# import xmltodict
# import requests
# import config as conf

# 1. save .las files into .txt files (fields: X(coordinates), Y(coordinates), Z(coordinates), I(tensity), C(lassification) Number)
def las_to_txt(input_file):
    output_file = input_file.replact(".las", "")
    cmd = "las2txt -i {0} -o {1} --parse xyzic".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file + ".txt"

# 2. create saga point clouds (Module Name: "Import Point Cloud from Text File")
def create_point_cloud(input_file):
    output_file = input_file.replace(".txt", "")
    cmd = "saga_cmd io_shapes 16 -POINTS={1} -FILE={0} -FIELDS='4;5' -FIELDNAMES='intensity;classification' -FIELDTYPES="2;2" -FIELDSEP=2".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file + ".spc"

# 3. create grid for point cloud (Module Name: "Point Cloud to Grid") -OUTPUT=0 only z; -AGGREGATION=3 lowest z
def create_grid(input_file):
    output_file = input_file.replace(".spc", "")
    cmd = "saga_cmd pointcloud_tools 4 -POINTS={0} -OUTPUT=0 -GRID={1} -AGGREGATION=3 -CELLSIZE=1.000000".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file + ".sgrd"

# 4. close gaps (Module Name: "Close Gaps") (requires .sgrd files as inputs)
def fill_grid_gaps(input_file):
    output_file = input_file.replace(".sgrd", "_DSM.sgrd")
    cmd = "saga_cmd grid_tools 7 -INPUT={0} -RESULT={1} -THRESHOLD=0.100000".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file

# 5. calculate solar radiation (Module Name: "Potential Incoming Solar Radiation")
# parameters:
# -GRD_TOTAL=output_file (enable total insolation output)
# -DAY_A=0 -MON_A=6 (start date July 1st)
# -DAY_B=0 -MON_B=6 (end date July 1st)
# -DDAYS=1 (Time Resolution: Range of Days)
# -DHOUR=3.000 (Time Resolution: Day)
# -HOUR_RANGE_MIN=5.000000 (Time Span)
# -HOUR_RANGE_MAX=20.000000 (Time Span)
# -METHOD=2 (Atmospheric Effects: Lumped Atmospheric Transmittance)

# other parameters are left as default
def solar_radiation(input_file):
    output_file_direct = input_file.replace("_DSM.sgrd", "_direct.sgrd")
    output_file_direct = input_file.replace("_DSM.sgrd", "_diffus.sgrd")
    output_file_totals = input_file.replace("_DSM.sgrd", "_solar.sgrd")
    cmd = "saga_cmd ta_lighting 2 -GRD_DEM={0} -GRD_DIRECT={1} -GRD_DIFFUS={2} -GRD_TOTAL={3} -DAY_A=0 -MON_A=6 -DAY_B=0 -MON_B=6 -DDAYS=1 -DHOUR=3.000 -HOUR_RANGE_MIN=5.000000 -HOUR_RANGE_MAX=20.000000 -METHOD=2".format(input_file, output_file_direct, output_file_diffus, output_file_totals)
    sb.call(cmd, shell=False)
    return output_file

# 6.export .tif image, only output total solar radiation image
def export_tif(input_file):
    output_file = input_file.replace(".sgrd", ".tif")
    # -COL_PALETTE=13 red & blue
    cmd = "saga_cmd io_grid_image 0 -GRID={0} -FILE={1} -COL_PALETTE=13".format(input_file, output_file)
    sb.call(cmd, shell=False)
    return output_file

# 7.generate tile files
def tile_generator(input_file):
    output_file = input_file.replact(".tif", "_tiles")
    # -z 0-5 (zoom level 0-5), -w none (diable HTML output)
    cmd = "gdal2tiles.py -p raster -z 0-5 -w none {0}".format(input_file)
    sb.call(cmd, shell=False)
    return output_file
