import pandas as pd
from python_sql_connection import get_connection


def fetch_instruments_data():
    # Fetch all instruments from the database and return as JSON.
    # Returns: DF --> JSON string
    conn = get_connection()
    try:
        query = """
        SELECT * 
        FROM instruments
        """
        
        df = pd.read_sql(query, conn)
        print(f"Fetched {len(df)} instruments")
        return df.to_json(orient='records')
    
    except Exception as e:
        print(f"Error fetching instruments: {e}")
        return None
        
    finally:
        conn.close()

def fetch_user_transactions(client_id: int ):
    conn = get_connection()
    try:
        query = """ SELECT t.transaction_id , c.first_name, t.amount 
        FROM transactions AS t INNER JOIN clients AS c 
        ON t.client_id = c.client_id
        WHERE t.client_id = %s;"""
        
        df = pd.read_sql(query, conn, params=(client_id,))
        print(f"Fetched {len(df)} transactions")
        return df.to_json(orient='records')
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return None
            
    finally:
        conn.close()


        



if __name__ == "__main__":
    # Example usage
    print("=== Fetching All Instruments ===")
    instruments = fetch_instruments_data()
    if instruments is not None:
        print(instruments)
 
