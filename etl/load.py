import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.database_connections import get_warehouse_connection
import pandas as pd
from extract import extractHoldingsAndOrders


def loadClients(client_rows):
    if not client_rows:
        return 0
    
    extracted_rows = [[row[0], row[1], row[2]] for row in client_rows]


    query = """
        INSERT INTO clients (
            client_id,
            first_name, 
            last_name
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (client_id)
        DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name
    """

    with get_warehouse_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, extracted_rows)

        conn.commit()

    return len(extracted_rows)



def loadEmployees(employee_rows):
    if not employee_rows:
        return 0

    extracted_rows = [[row[0], row[1], row[2], row[3]] for row in employee_rows]
    
    query = """
        INSERT INTO employees (
            employee_id,
            first_name, 
            last_name,
            role
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (employee_id)
        DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            role = EXCLUDED.role
    """

    with get_warehouse_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, extracted_rows)

        conn.commit()

    return len(extracted_rows)



def loadPrices(price_rows):
    if not price_rows:
        return 0
    # Extract all 10 columns from the new query:
    # price_id, ticker, askprice, asksize, bidprice, bidsize, askexchange, bidexchange, tapes, recorded_at

    query = """
        INSERT INTO prices (
            price_id,
            ticker, 
            askprice,
            asksize,
            bidprice,
            bidsize,
            askexchange,
            bidexchange,
            tapes,
            recorded_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (price_id)
        DO UPDATE SET
            ticker = EXCLUDED.ticker,
            askprice = EXCLUDED.askprice,
            asksize = EXCLUDED.asksize,
            bidprice = EXCLUDED.bidprice,
            bidsize = EXCLUDED.bidsize,
            askexchange = EXCLUDED.askexchange,
            bidexchange = EXCLUDED.bidexchange,
            tapes = EXCLUDED.tapes,
            recorded_at = EXCLUDED.recorded_at
    """

    with get_warehouse_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, price_rows)

        conn.commit()

    return len(price_rows)


def loadTransactions(transaction_rows):
    if not transaction_rows:
        return 0


    query = """
        INSERT INTO transactions (
            transaction_id,
            client_id,
            ttype,
            amount,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (transaction_id)
        DO UPDATE SET
            client_id = EXCLUDED.client_id,
            created_at = EXCLUDED.created_at,
            ttype = EXCLUDED.ttype,
            amount = EXCLUDED.amount
    """

    with get_warehouse_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, transaction_rows)

        conn.commit()

    return len(transaction_rows)



def loadHoldings(rows):
    if not rows:
        return 0
    
    # Extract columns at indexes 0, 2, 3 from each row
    extracted_rows = [[row[0], row[2], row[3]] for row in rows]
    
    query = """
        INSERT INTO holdings (
            quantity,
            ticker,
            client_id
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (client_id, ticker)
        DO UPDATE SET     
            quantity = EXCLUDED.quantity
    """

    with get_warehouse_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, extracted_rows)

        conn.commit()

    return len(extracted_rows)

def loadOrders(rows):
    if not rows:
        return 0
    
    # Extract columns from each row: order_id, ticker, client_id, order_type, order_status, price, quantity, order_date
    extracted_rows = [[row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]] for row in rows]

    query = """
        INSERT INTO orders (
            order_id,
            ticker,
            client_id,
            order_type,
            order_status,
            price,
            quantity,
            order_date
        )
        VALUES (%s, %s , %s, %s ,%s , %s, %s, %s)
        ON CONFLICT (order_id)
        DO UPDATE SET     
            ticker = EXCLUDED.ticker,
            client_id = EXCLUDED.client_id,
            order_type = EXCLUDED.order_type,
            order_status = EXCLUDED.order_status,
            price = EXCLUDED.price,
            quantity = EXCLUDED.quantity,
            order_date = EXCLUDED.order_date
    """

    with get_warehouse_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, extracted_rows)

        conn.commit()

    return len(extracted_rows)


