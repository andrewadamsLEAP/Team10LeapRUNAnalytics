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





if __name__ == "__main__":
    # Example usage
    print("=== Fetching All Instruments ===")
    instruments = fetch_instruments_data()
    if instruments is not None:
        print(instruments)
 
