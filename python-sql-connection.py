import psycopg
import pandas as pd

# Define connection variables
# Not a fan of not defining variable types

DB_HOST = "localhost"
DB_PORT = 8100
DB_NAME = "team10leap"
DB_USER = "postgres"
DB_PASSWORD = "n3u3d4!"
    
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
