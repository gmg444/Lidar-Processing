import psycopg2  as pg
import config as conf

# Example batch sequence:
# http://localhost:8080/start_job?tile_ids=15,16
# http://localhost:8080/job_status?job_id=9
# http://localhost:8080/cancel_job?job_id=9

def get_new_job_id():
    # Gets a new job identifier if the town has not yet been processed
    cnxn = pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])
    cursor = cnxn.cursor()
    job_id = -1
    try:
        sql = "select nextval('job_gid_seq')"
        cursor = cnxn.cursor()
        cursor.execute(sql)
        job_id = int(cursor.fetchone()[0])
    finally:
        cursor.close()
        cnxn.close()
    return job_id

def get_tile_list(wkt):
    sql = "select gid from tile_index where ST_Intersects(geom, ST_GeomFromText('{0}', 4326))".format(wkt)
    cnxn = pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])
    cursor = cnxn.cursor()
    cursor.execute(sql)
    results = []
    for row in cursor.fetchall():
        results.append(int(row[0]))
    cursor.close()
    cnxn.close()
    return results

def get_job_list():
    sql = "select gid, description from job where coalesce(description,'') <> '' order by gid, description"
    cnxn = pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])
    cursor = cnxn.cursor()
    cursor.execute(sql)
    results = []
    for row in cursor.fetchall():
        d = { "job_id": row[0],
              "description": row[1]}
        results.append(d)
    cursor.close()
    cnxn.close()
    return results

def start_job(job_id, tile_list, description, poly_wkt):
    # Starts a job by inserting rows into job and job_tile table
    cnxn = pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])
    cursor = cnxn.cursor()
    # Create the parent job record
    cursor.execute("insert into job (gid, status, description, geom_txt) values (%s, 'ready', %s, %s)", \
                   (job_id, description + " (" + str(job_id) + ")", poly_wkt))
    # Create the tile records
    params = []
    for t in tile_list:
        params.append((job_id, t, 'ready'))
    sql = "insert into job_tile(job_id, tile_id, status) values(%s, %s, %s)"
    cursor.executemany(sql, params)
    cursor.close()
    cnxn.commit()
    cnxn.close()

def cancel_job(job_id):
    # Deletes the job, causing it to be cancelled
    cnxn = pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])
    cursor = cnxn.cursor()
    cursor.execute("delete from job_tile where job_id = %s", (job_id,))
    cursor.execute("delete from job where gid=%s", (job_id,))
    cursor.close()
    cnxn.commit()
    cnxn.close()

def job_status(job_id):
    # Returns the status of the tilees in the job, count grouped by status
    sql = "select status from job where gid = %s"
    job_status = "Unkown"
    cnxn = pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])
    cursor = cnxn.cursor()
    cursor.execute(sql, (job_id,))
    job_status = cursor.fetchone()[0]
    cursor.close()

    sql = "select status, count(*) from job_tile where job_id = %s group by status order by status"
    cursor = cnxn.cursor()
    cursor.execute(sql, (job_id,))
    tile_status = []
    rows = cursor.fetchall()
    for r in rows:
        tile_status.append(tuple(r))
    cursor.close()

    sql = """select count(distinct gid)::float / (select count(*) from job_tile where job_id = %s)
          from job_tile where job_id = %s and status = 'complete' """
    cursor = cnxn.cursor()
    cursor.execute(sql, (job_id, job_id))
    percent_done = str(cursor.fetchone()[0])
    cursor.close()

    cnxn.close()
    return job_status, tile_status, percent_done





