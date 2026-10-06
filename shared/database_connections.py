import psycopg
import os
from dotenv import load_dotenv

load_dotenv()


# Create and return a PostgreSQL data warehouse connection 
# Returns psycopg.Connection: A PostgreSQL data warehouse connection object
def get_warehouse_connection():
    # Define connection variables from .env
    WAREHOUSE_DB_HOST = os.getenv("WAREHOUSE_DB_HOST")
    WAREHOUSE_DB_PORT = int(os.getenv("WAREHOUSE_DB_PORT"))
    WAREHOUSE_DB_NAME = os.getenv("WAREHOUSE_DB_NAME")
    WAREHOUSE_DB_USER = os.getenv("WAREHOUSE_DB_USER")
    WAREHOUSE_DB_PASSWORD = os.getenv("WAREHOUSE_DB_PASSWORD")
    
    try:
        conn = psycopg.connect(
            host=WAREHOUSE_DB_HOST,
            port=WAREHOUSE_DB_PORT,
            dbname=WAREHOUSE_DB_NAME,
            user=WAREHOUSE_DB_USER,
            password=WAREHOUSE_DB_PASSWORD    
        )
        print("Data Warehouse connection successful!")
        return conn
    except Exception as e:
        print(f"Error connecting to data warehouse: {e}")
        raise


# Create and return a PostgreSQL database connection 
# Returns psycopg.Connection: A PostgreSQL database connection object
def get_main_db_connection():
    # Define connection variables from .env
    MAIN_DB_HOST = os.getenv("MAIN_DB_HOST")
    MAIN_DB_PORT = int(os.getenv("MAIN_DB_PORT"))
    MAIN_DB_NAME = os.getenv("MAIN_DB_NAME")
    MAIN_DB_USER = os.getenv("MAIN_DB_USER")
    MAIN_DB_PASSWORD = os.getenv("MAIN_DB_PASSWORD")
    
    try:
        conn = psycopg.connect(
            host=MAIN_DB_HOST,
            port=MAIN_DB_PORT,
            dbname=MAIN_DB_NAME,
            user=MAIN_DB_USER,
            password=MAIN_DB_PASSWORD    
        )
        print("Database connection successful!")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise
    
    

if __name__ == "__main__":
    # Test connection
    dw_conn = get_warehouse_connection()
    if dw_conn:
        dw_conn.close()
        print("DW Connection Closed.")

    db_conn = get_main_db_connection()
    if db_conn:
        db_conn.close()
        print("Database Connection Closed.")


