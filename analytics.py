import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from python_sql_connection import get_connection

# def check_prices_table():
#     # Check if prices table has data
#     conn = get_connection()
#     try:
#         query = "SELECT COUNT(*) as row_count FROM prices"
#         result = pd.read_sql(query, conn)
#         count = result['row_count'][0]
        
#         print(f"\n=== Prices Table Check ===")
#         print(f"Total rows in prices table: {count}")
        
#         if count > 0:
#             # Show sample data
#             sample_query = "SELECT * FROM prices LIMIT 5"
#             sample_df = pd.read_sql(sample_query, conn)
#             print("\nSample data:")
#             print(sample_df)
#         else:
#             print("⚠️  Prices table is empty!")
            
#         return count
    
#     except Exception as e:
#         print(f"Error checking prices table: {e}")
#         return None
        
#     finally:
#         conn.close()


def get_top_instruments(column = None, n = 10 ):
    # top n instruments based on a specific column
    # returns: DF --> JSON string
    if column is None:
        print("Column must be specified")
        return None
    conn = get_connection()
    try:
        query = f"""
        SELECT ticker, price, open, high 
        FROM prices
        WHERE (ticker, recorded_at) IN (
            SELECT ticker, MAX(recorded_at)
            FROM prices
            GROUP BY ticker
        )
        ORDER BY price DESC
        LIMIT {n}
        """
        
        df = pd.read_sql(query, conn)
        print(f"DataFrame shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        print (df.head())
        if df.empty:
            print("No data returned")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(df['ticker'], df['price'])
        
        ax.set_xlabel('Ticker', fontsize=14)
        ax.set_ylabel('Price ($)', fontsize=14)
        ax.tick_params(axis='both', which='major', labelsize=12)
        ax.set_title(f'Top {n} Instruments by Price ($)', fontsize=14)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    except Exception as e:
        print(f"Error fetching top instruments: {e}")
        return None
        
    finally:
        conn.close()
        



def get_price_chart_by_ticker(ticker, chart_type='line', interval='1min'):
    connection = get_connection()
    try:
        query = f"""
        SELECT ticker, price, recorded_at
        FROM prices
        WHERE ticker = '{ticker}'
        ORDER BY recorded_at ASC
        """
        
        df = pd.read_sql(query, connection)
        print(f"DataFrame shape (raw): {df.shape}")
        
        if df.empty:
            print(f"No data found for ticker: {ticker}")
            return
        
        # convert recorded_at to datetime
        df['recorded_at'] = pd.to_datetime(df['recorded_at'])
        
        # aggregate data by minut and group by minute and take last price of each minute
        df['minute'] = df['recorded_at'].dt.floor('1min')
        df_agg = df.groupby('minute')['price'].last().reset_index()
        
        print(f"DataFrame shape (aggregated by minute): {df_agg.shape}")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if chart_type == 'line':
            ax.plot(df_agg['minute'], df_agg['price'], linewidth=2, markersize=6)
        elif chart_type == 'area':
            ax.fill_between(df_agg['minute'], df_agg['price'], alpha=0.5)
            ax.plot(df_agg['minute'], df_agg['price'], linewidth=2)
        elif chart_type == 'bar':
            ax.bar(df_agg['minute'], df_agg['price'], width=0.02)
        
        ax.set_xlim([df_agg['minute'].min(), df_agg['minute'].max()])
        ax.set_xlabel('Time (UTC)', fontsize=14)
        ax.set_ylabel('Price ($)', fontsize=14)
        ax.tick_params(axis='both', which='major', labelsize=12)
        ax.set_title(f'{ticker} Price Throughout the Day', fontsize=14)
        ax.grid(True, alpha=0.3)
        
        # x-axis to show time in HH:MM format
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    except Exception as e:
        print(f"Error creating chart: {e}")
        return None
        
    finally:
        connection.close()

if __name__ == "__main__":
    # print("=== Checking Prices Table ===")
    # check_prices_table()
    
    # print("\n=== Fetching All Instruments ===")
    # instruments = fetch_instruments_data()
    # if instruments is not None:
    #     print(instruments)
        
    print("\n=== Top 10 Instruments ===")
    get_top_instruments(column='price', n=10)
    
    print("\n=== Price Chart for Specific Ticker ===")
    get_price_chart_by_ticker(ticker='AAPL', chart_type='line')
