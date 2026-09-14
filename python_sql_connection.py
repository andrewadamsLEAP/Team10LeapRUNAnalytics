import psycopg
import os
from dotenv import load_dotenv

load_dotenv()


 # Create and return a PostgreSQL database connection 
 # Returns psycopg.Connection: A PostgreSQL database connection object
def get_connection():
    # Define connection variables from .env
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT"))
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    
    try:
        conn = psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD    
        )
        print("Database connection successful!")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise


if __name__ == "__main__":
    # Test connection
    conn = get_connection()
    if conn:
        conn.close()
        print("Connection closed.")


