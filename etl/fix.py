import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.database_connections import get_main_db_connection

import pandas as pd


def getOrders():
    query = """SELECT ticker, client_id, order_type, order_status, quantity FROM orders"""
    with get_main_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            orders = cur.fetchall()
            print(orders)
            return orders



def compute():
    orders = getOrders()
    df = pd.DataFrame(columns=["client_id", "ticker", "quantity"])
    
    for order in orders:
        order_status = order[3]  # order_status at index 3
        
        # Only process if order_status is FULFILLED
        if order_status != 'FULFILLED':
            print(f"⊘ Skipping order with status: {order_status}")
            continue
        
        client_id = order[1]
        ticker = order[0]
        quantity = order[4]
        
        # Check if same client_id and ticker already exists
        existing = df[(df["client_id"] == client_id) & (df["ticker"] == ticker)]
        
        if not existing.empty:
            # If exists, add up quantity
            idx = existing.index[0]
            df.loc[idx, "quantity"] += quantity
            print(f"✓ Updated {ticker} for client {client_id}: quantity now {df.loc[idx, 'quantity']}")
        else:
            # If doesn't exist, add as new row
            df = pd.concat([df, pd.DataFrame([{
                "client_id": client_id,
                "ticker": ticker,
                "quantity": quantity
            }])], ignore_index=True)
            print(f"✓ Added {ticker} for client {client_id}: quantity {quantity}")
    
    # Sort by client_id
    df = df.sort_values(by="client_id").reset_index(drop=True)
    
    print(f"\n=== Final Holdings ===\n{df}")
    return df.values.tolist()
   
   
   

def insertHolding(df):
    if not df:
        print("✗ No data to insert")
        return 0
    
    print(f"Attempting to insert {len(df)} records...")
    print(f"First record: {df[0]}")
    print(f"First record types: {[type(x).__name__ for x in df[0]]}")
    
    # Convert numpy types to Python native types
    df_clean = []
    for record in df:
        clean_record = []
        for val in record:
            if hasattr(val, 'item'):  # numpy type
                clean_record.append(val.item())
            else:
                clean_record.append(val)
        df_clean.append(tuple(clean_record))
    
    print(f"Cleaned first record: {df_clean[0]}")
    
    query = """
        INSERT INTO holdings (
            client_id,
            ticker, 
            quantity
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (client_id, ticker)
        DO UPDATE SET
            quantity = EXCLUDED.quantity
        """
    
    try:
        with get_main_db_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, df_clean)
        
            conn.commit()
        print(f"Successfully committed {len(df_clean)} records")
        return len(df_clean)
    except Exception as e:
        print(f"Error inserting holdings: {e}")
        import traceback
        traceback.print_exc()
        return 0
        
        
        
if __name__ == "__main__":
    df = compute()
    rows_inserted = insertHolding(df)
    print(f"✓ Inserted {rows_inserted} holdings into target database")
        
        