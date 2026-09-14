import pandas as pd
import json
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


def get_instruments_by_category(category):
    """
    Fetch instruments filtered by asset type (STOCK, FOREX, CRYPTO)
    
    Args:
        category (str): Asset type to filter by
        
    Returns:
        str: JSON string of filtered instruments
    """
    conn = get_connection()
    try:
        query = """
        SELECT * 
        FROM instruments
        WHERE asset_type = %s
        """
        
        df = pd.read_sql(query, conn, params=(category,))
        print(f"Fetched {len(df)} instruments in category '{category}'")
        return df.to_json(orient='records')
    
    except Exception as e:
        print(f"Error fetching instruments by category: {e}")
        return None
        
    finally:
        conn.close()


def analyze_instruments():
    """
    Perform analytics on instruments data
    
    Returns:
        str: JSON string with analytics results
    """
    conn = get_connection()
    try:
        query = """
        SELECT * 
        FROM instruments
        """
        
        df = pd.read_sql(query, conn)
        
        if df is None or df.empty:
            print("No data to analyze")
            return None
        
        analysis = {
            "total_count": len(df),
            "columns": df.columns.tolist(),
            "summary": df.describe().to_dict(),
        }
        
        return json.dumps(analysis)
    
    except Exception as e:
        print(f"Error analyzing instruments: {e}")
        return None
        
    finally:
        conn.close()


def run_custom_query(sql_query):
    """
    Execute a custom SQL query
    
    Args:
        sql_query (str): SQL query to execute
        
    Returns:
        str: JSON string with query results
    """
    conn = get_connection()
    try:
        df = pd.read_sql(sql_query, conn)
        print(f"Query executed successfully. Rows returned: {len(df)}")
        return df.to_json(orient='records')
        
    except Exception as e:
        print(f"Error executing query: {e}")
        return None
        
    finally:
        conn.close()


if __name__ == "__main__":
    # Example usage
    print("=== Fetching All Instruments ===")
    instruments = fetch_instruments_data()
    if instruments is not None:
        print(instruments)
 
