import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.watermark import get_last_watermark, update_last_watermark, get_max_timestamp
from extract import (extractClients, extractEmployees, extractPrices, extractTransactions, extractHoldingsAndOrders)
from transform import (transformClients, transformEmployees, transformPrices, transformTransactions, transformHoldingsAndOrders)
from load import (loadClients, loadEmployees, loadPrices, loadTransactions, loadHoldings, loadOrders)

def run():
    # Get separate watermarks for each table
    client_watermark = get_last_watermark('clients')
    employee_watermark = get_last_watermark('employees')
    price_watermark = get_last_watermark('prices')
    transaction_watermark = get_last_watermark('transactions')
    holdings_watermark = get_last_watermark('holdings')
    orders_watermark = get_last_watermark('orders')
    
    print(f"Client watermark: {client_watermark}")
    print(f"Employee watermark: {employee_watermark}")
    print(f"Price watermark: {price_watermark}")
    print(f"Transaction watermark: {transaction_watermark}")
    print(f"Holdings watermark: {holdings_watermark}")
    print(f"Orders watermark: {orders_watermark}")
    
    
    
    # EXTRACT with separate watermarks
    try:
        client_rows = extractClients(client_watermark)
        employee_rows = extractEmployees(employee_watermark)
        price_rows = extractPrices(price_watermark)
        transaction_rows = extractTransactions(transaction_watermark)
        order_holding_rows = extractHoldingsAndOrders(orders_watermark)
    except Exception as e:
        print(f"Error during extraction: {e}")
        return
    
    # TRANSFORM
    try:
        client_rows = transformClients(client_rows)
        employee_rows = transformEmployees(employee_rows)
        price_rows = transformPrices(price_rows)
        transaction_rows = transformTransactions(transaction_rows)
        order_holding_rows = transformHoldingsAndOrders(order_holding_rows)
    except Exception as e:
        print(f"Error during transformation: {e}")
        return
    
    # LOAD
    try:
        loadClients(client_rows)
        loadEmployees(employee_rows)
        loadPrices(price_rows)
        loadTransactions(transaction_rows)
        loadHoldings(order_holding_rows)
        loadOrders(order_holding_rows)
    except Exception as e:
        print(f"Error during loading: {e}")
        return
    
    
    
    # UPDATE each table's watermark separately
    try:
        if client_rows:
            new_client_watermark = get_max_timestamp(client_rows)
            if new_client_watermark:
                update_last_watermark('clients', new_client_watermark)
        
        if employee_rows:
            new_employee_watermark = get_max_timestamp(employee_rows)
            if new_employee_watermark:
                update_last_watermark('employees', new_employee_watermark)
        
        if price_rows:
            new_price_watermark = get_max_timestamp(price_rows)
            if new_price_watermark:
                update_last_watermark('prices', new_price_watermark)
        
        if transaction_rows:
            new_transaction_watermark = get_max_timestamp(transaction_rows)
            if new_transaction_watermark:
                update_last_watermark('transactions', new_transaction_watermark)
        
        if order_holding_rows:
            new_holdings_watermark = get_max_timestamp(order_holding_rows)
            if new_holdings_watermark:
                update_last_watermark('holdings', new_holdings_watermark)
                update_last_watermark('orders', new_holdings_watermark)
                
        
        print("\nETL completed successfully")
    except Exception as e:
        print(f"Error updating watermarks: {e}")


