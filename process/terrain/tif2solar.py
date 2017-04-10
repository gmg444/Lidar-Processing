import subprocess as sb

def tif_to_solar(input_file, output_file):
    # todo - get latitude from file
    solar_file = input_file.replace(".tif", "")
    cmd = "saga_cmd ta_lighting 2 -GRD_DEM={0} -GRD_SVF= -GRD_VAPOUR= -GRD_VAPOUR_DEFAULT=10.000000 -GRD_LINKE= -GRD_LINKE_DEFAULT=3.000000 -GRD_DIRECT= -GRD_DIFFUS= -GRD_TOTAL={1} -GRD_RATIO= -GRD_DURATION= -GRD_SUNRISE= -GRD_SUNSET= -SOLARCONST=1367.000000 -LOCALSVF=1 -UNITS=0 -SHADOW=1 -LOCATION=0 -LATITUDE=42.000000 -PERIOD=1 -DAY=07/15/2017 -DAY_STOP=07/15/2017 -DAYS_STEP=5 -MOMENT=12.000000 -HOUR_RANGE_MIN=6.000000 -HOUR_RANGE_MAX=20.000000 -HOUR_STEP=0.500000 -METHOD=2 -ATMOSPHERE=12000.000000 -PRESSURE=1013.000000 -WATER=1.680000 -DUST=100.000000 -LUMPED=70.000000".format(input_file, solar_file)
    sb.call(cmd, shell=False)
    grid_file = solar_file + ".sdat"
    cmd = "saga_cmd io_gdal 1 -GRIDS={0} -FILE={1} -FORMAT=7 -TYPE=0 -SET_NODATA=0 -NODATA=3.000000 -OPTIONS=".format(grid_file, output_file)
    sb.call(cmd, shell=False)
