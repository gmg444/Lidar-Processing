# pip install geopandas
import geopandas as gpd

tree_layer = gpd.read_file(r'C:\Projects\lidar-data\index\LIDARINDEX_POLY.shp')
tree_subset = tree_layer[['geometry','AREA_NAME']]
dissolved_tree_subset = tree_subset.dissolve(by='AREA_NAME')
dissolved_tree_subset.plot()
head = dissolved_tree_subset.head()
print head
dissolved_tree_subset.to_file(r'C:\Projects\lidar-data\index\test_output.shp')


# http://gis.stackexchange.com/questions/140666/dissolve-polygons-of-geojson-with-gdal-ogr
