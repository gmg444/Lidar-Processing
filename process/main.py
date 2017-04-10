import config as conf
import job_manager as jm
import time as tm
import database as db
import psycopg2 as pg

def main():
    job_manager = jm.JobManager()
    while (True):
        tm.sleep(conf.sleep_time_in_seconds) # Check for new jobs at intervals.
        job_manager.run_next_job()

def load_tiles():
    cnxn = db.get_connection()
    cursor = cnxn.cursor()
    with open(r"D:\lidar-maps-data\data-1491679294713.sql", "r") as f:
        ln = f.readlines()
        counter = 0
        for sql in ln:
            cursor.execute(sql)
            counter += 1
            if counter % 1000 == 0:
                print ("inserted", counter)
                cnxn.commit()
                cursor.close()
                cursor = cnxn.cursor()

if __name__ == "__main__":
    #load_tiles()
    main()
