import psycopg
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
# Define connection variables
# Not a fan of not defining variable types

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
    
# Create the connection 

conn = psycopg.connect(
    host = DB_HOST,
    port = DB_PORT,
    dbname = DB_NAME,
    user = DB_USER,
    password = DB_PASSWORD    
)

# Make a query

query = """
SELECT * 
FROM instruments

"""

# Pass the query and connection as a dataframe to the postgres
# database.

df = pd.read_sql(query, conn)
print(df)
