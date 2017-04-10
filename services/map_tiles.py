import psycopg2  as pg
import config as conf

def get_polygon_data(coords):
    coords = coords.replace("],[", "~").replace(",", " ").replace("~", ",").replace("[", "(").replace("]", ")");
    sWkt = "MULTIPOLYGON{0}".format(coords)
    sql = """SELECT st_asgeojson(st_geomfromtext('{0}', 4326)), count(distinct b.gid),Coalesce(ST_Area(ST_Union(b.geom))/10000.0, 0),
        minorcivna, state_name,  Coalesce(areasqkm, 0)
        FROM us_town a left outer join tile_index b
        on ST_Within(b.geom, a.geom)
        WHERE ST_Intersects(b.geom,
        st_geomfromtext('{2}', 4326))
        group by a.geom,  minorcivna, state_name,  areasqkm""".format(sWkt, sWkt, sWkt)
    result = {}
    cnxn = pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])
    cursor = cnxn.cursor()
    cursor.execute(sql)
    row = cursor.fetchone()
    result["polyGeoJson"] = str(row[0])
    result["numTiles"] = int(row[1])
    result["processArea"] = float(row[2])
    result["townName"] = str(row[3])
    result["stateName"] = str(row[4])
    result["townArea"] = float(row[5])
    result["polyWkt"] = sWkt
    cursor.close()
    cnxn.close()
    return result

def get_town_data(lat, lon):
    #  locate town containing coordinate
    sql = """SELECT ST_AsGeoJson(a.geom), count(distinct b.gid),Coalesce(ST_Area(ST_Union(b.geom))/10000.0, 0),
        minorcivna, state_name,  Coalesce(areasqkm, 0), ST_AsText(a.geom)
        FROM us_town a left outer join tile_index b
        on ST_Within(b.geom, a.geom)
        WHERE ST_Contains(a.geom, st_geomfromtext('POINT({0} {1})', 4326))
        group by a.geom,  minorcivna, state_name,  areasqkm""".format(str(lon), str(lat))
    result = {}
    cnxn = pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])
    cursor = cnxn.cursor()
    cursor.execute(sql)
    row = cursor.fetchone()
    result["polyGeoJson"] = str(row[0])
    result["numTiles"] = int(row[1])
    result["processArea"] = float(row[2])
    result["townName"] = str(row[3])
    result["stateName"] = str(row[4])
    result["townArea"] = float(row[5])
    result["polyWkt"] = str(row[6])
    cursor.close()
    cnxn.close()
    return result

def fetch_tile_list(lat, lon):
    cnxn = None
    try:
        cnxn = pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])
        cursor = cnxn.cursor()
        # find the tiles that are within the town corresponding to the coordinate
        sql = """SELECT ST_AsGeoJson(geom)
                 FROM us_town
                 WHERE ST_Contains(geom, st_geomfromtext('POINT({0} {1})', 4326))""".format(str(lon), str(lat))
        sql = """ SELECT count(distinct index), ST_Area(ST_Union(geom))
                  FROM  tile_index
                  WHERE ST_Within(geom, st_geomfromtext('{0}',4326))""".format(cursor.fetchone()[0])
        cursor.execute(sql)

        # return the tile indices
        results = []
        for row in cursor.fetchall():
            results.append(row[0])
        cursor.close()
        return results
    except (Exception, pg.DatabaseError) as error:
        return error
    finally:
        if cnxn is not None:
            cnxn.close()