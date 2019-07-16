import psycopg2
from datetime import datetime

import config

db = psycopg2.connect(config.DB_URL)


def get_bots_ids():
    print('[DB] Load all bots ids')
    with db:
        with db.cursor() as cur:
            cur.execute("SELECT username, id FROM bots WHERE status = 'checking';")
            return cur.fetchall()


def get_creator(bot_id):
    with db:
        with db.cursor() as cur:
            cur.execute("SELECT creator, username FROM bots WHERE id = %s;", (bot_id,)) 
            return cur.fetchone()

def set_time_wait(bot_id, time_wait):
    print('[DB] set time wait')
    with db:
        with db.cursor() as cur:
            cur.execute("""
                UPDATE bots SET waiting_time = %s, last_update = NOW() WHERE id = %s;
                INSERT INTO bot_check_stat (time_wait, bot_id) Values (%s, %s);
                """,
                (time_wait,  bot_id, time_wait,  bot_id)
            )

            

def set_not_work(bot_id):
    with db:
        with db.cursor() as cur:
            cur.execute("UPDATE bots SET status = 'not_work' WHERE id = %s;", (bot_id,)) 

    