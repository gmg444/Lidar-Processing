import config as conf
import os
import utils
import threading
import las2grid as lg
import glob as gl
import database as db
from multiprocessing import Pool
import tif2tree as tft
import tif2terrain as tfterr
import json

def process_tiles(tiles):
    # Downloads and grids tiles
    for t in tiles:
        try:
            work_path = t["path"]
            url, id = t["url"], t["id"]
            file_name = os.path.basename(url)
            cur_file = work_path + file_name
            # jm.update_tile_status(id, "downloading")
            utils.download_file(url, cur_file)
            if cur_file.endswith(".laz"):
                # jm.update_tile_status(id, "converting to las")
                cur_file = utils.convert_to_las(cur_file, work_path)
            #jm.update_tile_status(id, "generating grids")
            t["tree_pct"], t["tree_area"], t["all_area"] = lg.generate_grids(cur_file)
        except Exception as e:
            print ("Exception processing tile {0}: {1}".format(str(t['id']), str(e)))
            # log_message("Exception processing tile {0}: {1}".format(str(t['id']), str(e)))

class JobManager():
    def __init__(self):
        self.job_id = None
        self.tile_list = None
        self.thread_list = None
        self.work_path = None

    def log_message(self, message):
        # Logs message about this job to the job_log table
        print (message)
        if self.job_id:
            sql = "insert into job_log(job_id, message) values ({0}, '{1}')".format(self.job_id, message)
            db.exec_sql(sql)

    def run_next_job(self):
        # Updates the earliest job from status 0 to status 1, and returns the gid of the updated row. Returns nothing
        # if no pending jobs are available.
        sql = """update job set status = 'in progress'
            where gid in (select min(gid) from job where status = 'ready')
            returning gid"""
        current_job = db.exec_sql(sql, [], True)
        self.update_status("processing tiles")
        if type(current_job) is tuple:
            self.job_id = current_job[0]
            self.thread_list = []
            self.log_message("started job")
            self.work_path = conf.work_path + str(self.job_id) + "/"
            if not os.path.exists(self.work_path):
                os.makedirs(self.work_path)
            tile_list = self.get_tiles_to_process()
            minx, miny, maxx, maxy = self.get_bounds()
            if conf.num_threads > 1:
                if len(tile_list) < conf.num_threads:
                    self.num_threads = len(tile_list)
                else:
                    self.num_threads = conf.num_threads
                tile_count_step = len(tile_list) // self.num_threads # Integer division to get floow
                args = [[] for x in range(conf.num_threads)]
                for i in range(len(tile_list)):
                    args[i % self.num_threads].append(tile_list[i])
                pool = Pool(self.num_threads)
                pool.map(process_tiles, args)
                pool.close()
                pool.join()
            else:
                process_tiles(tile_list)

            self.update_status("saving clip file")
            sql = "select geom_txt from job where gid = {0}".format(self.job_id)
            wkt = db.exec_sql(sql, [], True)[0]
            clip_poly = self.work_path + "clip_poly.shp"
            utils.save_clip_poly(wkt, clip_poly)

            # self.update_status("mosaicking tiles")
            # utils.mosaic_tiles(self.work_path + "*_dsm.tif", self.work_path + "mosaic_dsm.tif", minx, miny, maxx, maxy,
            #                    clip_poly, self.job_id)
            # utils.mosaic_tiles(self.work_path + "*_height.tif", self.work_path + "mosaic_height.tif", minx, miny, maxx,
            #                    maxy, clip_poly, self.job_id)
            # # utils.mosaic_tiles(self.work_path + "*_intensity.tif", self.work_path + "mosaic_intensity.tif", minx, miny, maxx, maxy, clip_poly)
            # utils.mosaic_tiles(self.work_path + "*_dem.tif", self.work_path + "mosaic_dem.tif", minx, miny, maxx, maxy,
            #                    clip_poly, self.job_id)

            self.update_status("finalizing output")
            tree_file = self.work_path + "mosaic_trees.shp"
            utils.merge_tiles(self.work_path + "*_trees.shp", tree_file, clip_poly)
            utils.finalize(tree_file, clip_poly, self.job_id)

            # bldgs_file = self.work_path + "mosaic_bldgs.shp"
            # utils.merge_tiles(self.work_path + "*_bldgs.shp", bldgs_file, clip_poly, 10)
            # utils.finalize(bldgs_file, clip_poly, self.job_id)

            # impervious_file = self.work_path + "mosaic_impervious.shp"
            # utils.merge_tiles(self.work_path + "*_impervious.shp", impervious_file, clip_poly, 10)
            # utils.finalize(impervious_file, clip_poly, self.job_id)

            # contours_file = self.work_path + "mosaic_contours.shp"
            # utils.contours(self.work_path + "mosaic_dem.tif", contours_file, clip_poly)
            # utils.finalize(contours_file, clip_poly, self.job_id)

            for f_name in gl.glob(self.work_path + "*.txt"):
                out_file = conf.output_path + str(job_id) + "_" + os.path.basename(f_name)
                cmd = "copy {0} {1}".format(f_name.replace("/", "\\"), out_file.replace("/", "\\"))
                utils.exec_command_line(cmd, shell_flag=True)

            self.update_status("job complete!")
            # utils.mosaic_tiles(self.work_path + "*_trees.tif", self.work_path + "mosaic_trees.tif", minx, miny, maxx, maxy)
            # self.update_status("generating map tiles")
            # utils.create_output_tiles(self.work_path + "mosaic_dsm.tif", self.work_path + "dsm/")
            # utils.create_output_tiles(self.work_path + "mosaic_height.tif", self.work_path + "height/")
            # # utils.create_output_tiles(self.work_path + "mosaic_intensity.tif", self.work_path + "intensity/")
            # utils.create_output_tiles(self.work_path + "mosaic_dem.tif", self.work_path + "dem/")
            # # utils.create_output_tiles(self.work_path + "mosaic_trees.tif", self.work_path + "trees/")

        else:
            self.job_id = None
            self.log_message("No jobs found")

    def get_tiles_to_process(self):
        results = []
        # Get tiles associated with the given job
        sql = "select tile_id, url from job_tile a inner join tile_index b on a.tile_id = b.gid where a.job_id = %s"
        t = db.get_rows(sql, [self.job_id])
        results = []
        for d in t:
            results.append({"id": d[0], "url": d[1].replace("\n", ""), "path": self.work_path })
        return results

    def get_bounds(self):
        sql = """
            select
            ST_XMin(st_envelope(st_transform(ST_Union(geom), 3857))),
            ST_YMin(st_envelope(st_transform(ST_Union(geom), 3857))),
            ST_XMax(st_envelope(st_transform(ST_Union(geom), 3857))),
            ST_YMax(st_envelope(st_transform(ST_Union(geom), 3857)))
            from job_tile a inner join tile_index b on a.tile_id = b.gid where a.job_id = %s
            """
        row = db.get_one_row(sql, [self.job_id])[0]
        minx, miny, maxx, maxy = float(row[0]), float(row[1]), float(row[2]), float(row[3])
        return minx, miny, maxx, maxy

    def update_tile_status(self, tile_id, status):
        # Returns the status of the tilees in the job, count grouped by status
        sql = "update job_tile set status=%s where tile_id=%s"
        db.exec_sql(sql, [status, tile_id])

    def update_status(self, status):
        # Returns the status of the tilees in the job, count grouped by status
        sql = "update job set status=%s where gid=%s"
        db.exec_sql(sql, [status, self.job_id])

    def add_map_layer(self, layer_name, map_url):
        sql = "insert into map_layer (job_id, town_id, name, url) values (%s, (select max(town_id) from job where gid=%s), %s, %s)"
        db.exec_sql(sql, [self.job_id, self.job_id, layer_name, map_url])

    def complete_job(self, town_id, map_url):
        sql = "update job set status = 2 where job_id = %s"
        db.exec_sql(sql, [self.job_id])

if __name__ == "__main__":
    job_id = 1000
    with open(r"D:/lidar-maps-data/amherst/amherst_tiles.geojson") as f:
        data = f.readlines()
        d = json.loads("".join(data))
        index = 1
        work_path = "D:/lidar-maps-data/amherst/"
        tile_list = []
        minx = 99999999
        maxx = -99999999
        miny = 99999999
        maxy = -99999999
        for f in d["features"]:
            id = f["properties"]["Tile"]
            # if id != "D14": # Test tile
            #     continue
            url = "http://gis.amherstma.gov/data/2009/lidar/LAS/AllPts/LAZ/AllPts_{0}.laz".format(id)
            item = {"id": index, "url": url, "path": work_path}
            bbox = [float(x) for x in f["bbox"]]
            if bbox[0] < minx:
                minx = bbox[0]
            if bbox[1] < miny:
                miny = bbox[1]
            if bbox[2] > maxx:
                maxx = bbox[2]
            if bbox[3] > maxy:
                maxy = bbox[3]
            tile_list.append(item)
            index += 1
    process_tiles(tile_list)
    with open(work_path + "_tiles_attribs.txt", "w") as f:
        lines = []
        for t in tile_list:
            line = "\t".join([str(x) for x in t.values()])
            lines.append(line + "\n")
        f.writelines(lines)
    print ("All Done!")
    exit()
    utils.mosaic_tiles(work_path + "*_dsm.tif", work_path + "mosaic_dsm.tif", minx, miny, maxx, maxy,
                       None, job_id)
    utils.mosaic_tiles(work_path + "*_height.tif", work_path + "mosaic_height.tif", minx, miny, maxx,
                       maxy, None, job_id)
    # utils.mosaic_tiles(self.work_path + "*_intensity.tif", self.work_path + "mosaic_intensity.tif", minx, miny, maxx, maxy, clip_poly)
    utils.mosaic_tiles(work_path + "*_dem.tif", work_path + "mosaic_dem.tif", minx, miny, maxx, maxy,
                       None, job_id)

    tree_file = work_path + "mosaic_trees.shp"
    utils.merge_tiles(work_path + "*_trees.shp", tree_file, None)
    utils.finalize(tree_file, None, job_id)

    bldgs_file = work_path + "mosaic_bldgs.shp"
    utils.merge_tiles(work_path + "*_bldgs.shp", bldgs_file, None, 10)
    utils.finalize(bldgs_file, None, job_id)

    # impervious_file = self.work_path + "mosaic_impervious.shp"
    # utils.merge_tiles(self.work_path + "*_impervious.shp", impervious_file, clip_poly, 10)
    # utils.finalize(impervious_file, clip_poly, self.job_id)

    contours_file = work_path + "mosaic_contours.shp"
    utils.contours(work_path + "mosaic_dem.tif", contours_file, None)
    utils.finalize(contours_file, None, job_id)
    print("job complete!")