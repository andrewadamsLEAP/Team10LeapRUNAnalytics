import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.database_connections import get_main_db_connection
from utils.queryRunner import run_query


def extractClients(last_watermark):
    query = f"""SELECT client_id, first_name, last_name, updated_at FROM clients WHERE updated_at > %s ORDER BY client_id"""
    return run_query(query, (last_watermark,))
    
def extractEmployees(last_watermark):
    query = f""" SELECT employee_id, first_name, last_name, role, updated_at FROM employees WHERE updated_at > %s ORDER BY employee_id"""
    return run_query(query, (last_watermark,))
    
def extractPrices(last_watermark):
    query = f""" SELECT price_id, ticker, ask_price, ask_size, bid_price, bid_size, ask_exchange, bid_exchange, tape, recorded_at FROM prices WHERE recorded_at > %s ORDER BY recorded_at, price_id"""
    return run_query(query, (last_watermark,))
    
def extractTransactions(last_watermark):
    query = f""" SELECT transaction_id, client_id,
                ttype,
                amount,
                created_at FROM transactions WHERE created_at > %s ORDER BY created_at, transaction_id"""   
    return run_query(query, (last_watermark,))
    
def extractHoldingsAndOrders(last_watermark):
    query = f""" SELECT h.quantity, o.*
        FROM holdings h
        JOIN orders o
        ON h.client_id = o.client_id AND h.ticker = o.ticker WHERE o.order_date > %s"""
    return run_query(query, (last_watermark,))
    


if __name__ == "__main__":
    extractTransactions(last_watermark= '1970-08-08')

