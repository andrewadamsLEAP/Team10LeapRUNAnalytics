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
    # Top n instruments based on a specific column
    # Returns: DF --> JSON string
    if column is None:
        print("Column must be specified")
        return None
    conn = get_connection()
    try:
        query = f"""
        SELECT ticker, bid_price
        FROM prices
        WHERE (ticker, recorded_at) IN (
            SELECT ticker, MAX(recorded_at)
            FROM prices
            GROUP BY ticker
        )
        ORDER BY bid_price DESC
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
        ax.bar(df['ticker'], df['bid_price'])
        
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
        SELECT ticker, bid_price, recorded_at
        FROM prices
        WHERE ticker = '{ticker}'
        ORDER BY recorded_at ASC
        """
        
        df = pd.read_sql(query, connection)
        print(f"DataFrame shape (raw): {df.shape}")
        
        if df.empty:
            print(f"No data found for ticker: {ticker}")
            return
        
        # Convert recorded_at to datetime
        df['recorded_at'] = pd.to_datetime(df['recorded_at'])
        
        # Aggregate data by minut and group by minute and take last price of each minute
        df['minute'] = df['recorded_at'].dt.floor('1min')
        df_agg = df.groupby('minute')['bid_price'].last().reset_index()
        
        print(f"DataFrame shape (aggregated by minute): {df_agg.shape}")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if chart_type == 'line':
            ax.plot(df_agg['minute'], df_agg['bid_price'], linewidth=2, markersize=6)
        elif chart_type == 'area':
            ax.fill_between(df_agg['minute'], df_agg['bid_price'], alpha=0.5)
            ax.plot(df_agg['minute'], df_agg['bid_price'], linewidth=2)
        elif chart_type == 'bar':
            ax.bar(df_agg['minute'], df_agg['bid_price'], width=0.02)
        
        ax.set_xlim([df_agg['minute'].min(), df_agg['minute'].max()])
        ax.set_xlabel('Time (UTC)', fontsize=14)
        ax.set_ylabel('Price ($)', fontsize=14)
        ax.tick_params(axis='both', which='major', labelsize=12)
        ax.set_title(f'{ticker} Price Throughout the Day', fontsize=14)
        ax.grid(True, alpha=0.3)
        
        # X-axis to show time in HH:MM format
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

def get_kpi_metrics(days=30):
    conn = get_connection()
    try:
        kpi_data = {}
        
        # Total trades or orders placed
        trades_df = pd.read_sql("SELECT COUNT(*) as count FROM orders", conn)
        kpi_data['total_trades'] = int(trades_df['count'][0])
        
        # Total trading volume (sum of quantity * price)
        volume_df = pd.read_sql("SELECT SUM(quantity * price) as total FROM orders", conn)
        kpi_data['total_volume'] = float(volume_df['total'][0]) if volume_df['total'][0] else 0
        
        # Average trade value
        avg_df = pd.read_sql("SELECT AVG(quantity * price) as avg FROM orders", conn)
        kpi_data['avg_trade_value'] = float(avg_df['avg'][0]) if avg_df['avg'][0] else 0
        
        # Total clients
        clients_df = pd.read_sql("SELECT COUNT(*) as count FROM clients", conn)
        kpi_data['total_clients'] = int(clients_df['count'][0])
        
        # Active clients who have traded within last N days
        active_clients_df = pd.read_sql(
            f"""SELECT COUNT(DISTINCT client_id) as count 
               FROM orders 
               WHERE order_date >= CURRENT_DATE - INTERVAL '{days} days'""", conn
        )
        kpi_data['active_clients'] = int(active_clients_df['count'][0])
        kpi_data['active_clients_percentage'] = round(
            (kpi_data['active_clients'] / kpi_data['total_clients'] * 100) 
            if kpi_data['total_clients'] > 0 else 0, 
            2
        )
        
        # Top 5 active clients
        top_active_df = pd.read_sql(
            f"""SELECT
                c.client_id,
                c.first_name,
                c.last_name,
                COUNT(DISTINCT o.order_id) as trade_count,
                SUM(o.quantity * o.price) as volume
            FROM clients c
            INNER JOIN orders o ON c.client_id = o.client_id
            WHERE o.order_date >= CURRENT_DATE - INTERVAL '{days} days'
            GROUP BY c.client_id, c.first_name, c.last_name
            ORDER BY volume DESC
            LIMIT 5""", conn
        )
        kpi_data['top_active_clients'] = top_active_df.to_dict(orient='records')
        
        # Inactive clients who have no trades in last N days
        inactive_df = pd.read_sql(
            f"""SELECT COUNT(DISTINCT client_id) as count
               FROM clients c
               WHERE NOT EXISTS (
                   SELECT 1 FROM orders o 
                   WHERE o.client_id = c.client_id 
                   AND o.order_date >= CURRENT_DATE - INTERVAL '{days} days'
               )""", conn
        )
        kpi_data['inactive_clients'] = int(inactive_df['count'][0])
        
        return kpi_data
        
    except Exception as e:
        print(f"Error calculating KPIs: {e}")
        return None
        
    finally:
        conn.close()

def get_instrument_metrics(days=30):
    conn = get_connection()
    try:
        query = f"""
        SELECT 
            i.ticker,
            i.asset_type,
            COUNT(DISTINCT o.order_id) as trade_count,
            SUM(o.quantity) as total_quantity,
            SUM(o.quantity * o.price) as total_volume,
            AVG(o.quantity * o.price) as avg_trade_value,
            MIN(o.price) as min_price,
            MAX(o.price) as max_price,
            COUNT(DISTINCT o.client_id) as unique_traders
        FROM instruments i
        LEFT JOIN orders o ON i.ticker = o.ticker
            AND o.order_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY i.ticker, i.asset_type
        ORDER BY total_volume DESC NULLS LAST
        """
        
        df = pd.read_sql(query, conn)
        
        df = df.fillna(0)
        
        numeric_cols = ['trade_count', 'total_quantity', 'total_volume', 'avg_trade_value', 'min_price', 'max_price', 'unique_traders']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df.to_dict(orient='records')
    
    except Exception as e:
        print(f"Error fetching instrument metrics: {e}")
        return None
    
    finally:
        conn.close()

def get_timeseries_metrics(days=30, granularity='daily'):
    conn = get_connection()
    try:
        if granularity == 'daily':
            date_format = "DATE(o.order_date)"
        elif granularity == 'weekly':
            date_format = "DATE_TRUNC('week', o.order_date)::DATE"
        elif granularity == 'monthly':
            date_format = "DATE_TRUNC('month', o.order_date)::DATE"
        else:
            granularity = 'daily'
            date_format = "DATE(o.order_date)"
        
        query = f"""
        SELECT 
            {date_format} as period,
            COUNT(DISTINCT o.order_id) as trade_count,
            SUM(o.quantity * o.price) as total_volume,
            AVG(o.quantity * o.price) as avg_trade_value,
            COUNT(DISTINCT o.client_id) as active_clients,
            COUNT(DISTINCT o.ticker) as instruments_traded
        FROM orders o
        WHERE o.order_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY period
        ORDER BY period ASC
        """
        
        df = pd.read_sql(query, conn)
        df = df.fillna(0)
        
        numeric_cols = ['trade_count', 'total_volume', 'avg_trade_value', 'active_clients', 'instruments_traded']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['period'] = df['period'].astype(str)
        
        return df.to_dict(orient='records')
    
    except Exception as e:
        print(f"Error fetching timeseries metrics: {e}")
        return None
    
    finally:
        conn.close()

def get_client_segments(days=30):
    conn = get_connection()
    try:
        query = f"""
        SELECT 
            c.client_id,
            c.first_name,
            c.last_name,
            COUNT(DISTINCT o.order_id) as trade_count,
            SUM(o.quantity * o.price) as total_volume,
            AVG(o.quantity * o.price) as avg_trade_value,
            COUNT(DISTINCT o.ticker) as instruments_traded,
            MAX(o.order_date) as last_trade_date
        FROM clients c
        LEFT JOIN orders o ON c.client_id = o.client_id
            AND o.order_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY c.client_id, c.first_name, c.last_name
        """
        
        df = pd.read_sql(query, conn)
        
        # Put clients into categories based on segments and volume
        def categorize_segment(volume):
            if volume is None or volume == 0:
                return "Inactive"
            elif volume < 5000:
                return "Casual"
            elif volume < 15000:
                return "Regular"
            else:
                return "High-Value"
        
        df['segment'] = df['total_volume'].apply(categorize_segment)
        df = df.fillna(0)
        
        segment_summary = df.groupby('segment').agg({
            'client_id': 'count',
            'total_volume': 'sum',
            'trade_count': 'sum',
            'avg_trade_value': 'mean'
        }).reset_index()
        segment_summary.columns = ['segment', 'client_count', 'total_volume', 'total_trades', 'avg_trade_value']
        
        detailed_clients = df[['client_id', 'first_name', 'last_name', 'segment', 'trade_count', 'total_volume', 'avg_trade_value', 'instruments_traded']].to_dict(orient='records')
        
        for col in ['client_count', 'total_volume', 'total_trades', 'avg_trade_value']:
            segment_summary[col] = pd.to_numeric(segment_summary[col], errors='coerce').fillna(0)
        
        return {
            'summary': segment_summary.to_dict(orient='records'),
            'detailed': detailed_clients
        }
    
    except Exception as e:
        print(f"Error calculating client segments: {e}")
        return None
    
    finally:
        conn.close()

def get_instrument_details(ticker, days=30):
    conn = get_connection()
    try:
        query = f"""
        SELECT 
            i.ticker,
            i.asset_type,
            COUNT(DISTINCT o.order_id) as trade_count,
            SUM(o.quantity) as total_quantity,
            SUM(o.quantity * o.price) as total_volume,
            AVG(o.quantity * o.price) as avg_trade_value,
            MIN(o.price) as min_price,
            MAX(o.price) as max_price,
            COUNT(DISTINCT o.client_id) as unique_traders
        FROM instruments i
        LEFT JOIN orders o ON i.ticker = o.ticker
            AND o.order_date >= CURRENT_DATE - INTERVAL '{days} days'
        WHERE i.ticker = %s
        GROUP BY i.ticker, i.asset_type
        """
        
        metrics_df = pd.read_sql(query, conn, params=(ticker,))
        
        if metrics_df.empty:
            return None
        
        top_traders_query = f"""
        SELECT 
            c.client_id,
            c.first_name,
            c.last_name,
            COUNT(DISTINCT o.order_id) as trade_count,
            SUM(o.quantity * o.price) as volume
        FROM clients c
        INNER JOIN orders o ON c.client_id = o.client_id
        WHERE o.ticker = %s
            AND o.order_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY c.client_id, c.first_name, c.last_name
        ORDER BY volume DESC
        LIMIT 10
        """
        
        traders_df = pd.read_sql(top_traders_query, conn, params=(ticker,))

        daily_trend_query = f"""
        SELECT 
            DATE(o.order_date) as date,
            COUNT(DISTINCT o.order_id) as trade_count,
            SUM(o.quantity * o.price) as daily_volume
        FROM orders o
        WHERE o.ticker = %s
            AND o.order_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY DATE(o.order_date)
        ORDER BY date ASC
        """
        
        daily_df = pd.read_sql(daily_trend_query, conn, params=(ticker,))
        daily_df['date'] = daily_df['date'].astype(str)
        
        metrics = metrics_df.to_dict(orient='records')[0]
        
        return {
            'instrument': metrics,
            'top_traders': traders_df.to_dict(orient='records'),
            'daily_trend': daily_df.to_dict(orient='records')
        }
    
    except Exception as e:
        print(f"Error fetching instrument details: {e}")
        return None
    
    finally:
        conn.close()

if __name__ == "__main__":
    # print("=== Checking Prices Table ===")
    # check_prices_table()
    
    # print("\n=== Fetching All Instruments ===")
    # instruments = fetch_instruments_data()
    # if instruments is not None:
    #     print(instruments)
        
    print("\n=== Top 10 Instruments ===")
    get_top_instruments(column='bid_price', n=10)
    
    print("\n=== Price Chart for Specific Ticker ===")
    get_price_chart_by_ticker(ticker='AAPL', chart_type='line')