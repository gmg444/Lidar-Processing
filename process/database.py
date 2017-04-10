import psycopg2 as pg
import config as conf

def get_connection():
    return pg.connect(host=conf.db["host"], database=conf.db["database"], user=conf.db["user"], password=conf.db["password"])

def exec_sql(sql, params=None, get_results=False):
    cnxn = get_connection()
    cursor = cnxn.cursor()
    cursor.execute(sql, params)
    result = None
    if get_results:
        result = cursor.fetchone()
    cursor.close()
    cnxn.commit()
    cnxn.close()
    return result

def get_rows(sql, params):
    cnxn = get_connection()
    cursor = cnxn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    results = []
    for row in rows:
        results.append(tuple(row))
    cursor.close()
    cnxn.close()
    return results

def get_one_row(sql, params):
    cnxn = get_connection()
    cursor = cnxn.cursor()
    cursor.execute(sql, params)
    result = []
    row = cursor.fetchone()
    result.append(tuple(row))
    cursor.close()
    cnxn.close()
    return result

