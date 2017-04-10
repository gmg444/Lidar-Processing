1. The pipeline of DTM_generator.py:
   --> Lidar Data(.las)
   --> Ground Point Classification(.las)
   --> Save to text file(.txt)
   --> Import as Point Cloud(.spc)
   --> Create Grids(.sgrd)
   --> Remove Ground Points(.sgrd)
   --> Close Gaps(DTM)(.sgrd)
   --> Create Slope/Aspect Grids(.sgrd)
   --> Export Raster Images(.tif)
   --> Generate Tiles Using gdal2tiles.py

2. The pipeline of DSM_generator.py:
   --> Lider Data(.las)
   --> Save to text file(.txt)
   --> Import as Point Cloud(.spc)
   --> Create Grids(.sgrd)
   --> Close Gaps(DSM)(.sgrd)
   --> Create Solar Radiation Grids(.sgrd)
   --> Export *Total Solar Radiation Raster Image(.tif)
   --> Generate Tiles Using gdal2tiles.py

3. The following may be updated:

   (1). Add -f=s to saga_cmd to silent all process and output messages.
   (2). Remove unwanted files when final output (tiles) is obtained.
   (3). Some parameters may need to be changed.
