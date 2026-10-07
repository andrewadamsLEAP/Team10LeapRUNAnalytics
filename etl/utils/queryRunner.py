import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.database_connections import get_main_db_connection

def run_query(query, last_watermark):
    with get_main_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (last_watermark,))
                return cur.fetchall()