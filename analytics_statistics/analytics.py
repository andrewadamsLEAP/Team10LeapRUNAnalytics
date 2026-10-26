import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta
from shared.database_connections import get_warehouse_connection

# def check_prices_table():
#     # Check if prices table has data
#     conn = get_warehouse_connection()
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

def _order_conditions(days=30, ticker=None, client_id=None, start_date=None,
                      end_date=None, order_status=None):
    """Build bound SQL parameters; end_date includes the entire selected day."""
    clauses, params = [], []
    if start_date is not None:
        clauses.append("o.order_date >= %s")
        params.append(start_date)
    else:
        clauses.append("o.order_date >= CURRENT_DATE - (%s * INTERVAL '1 day')")
        params.append(days)
    if end_date is not None:
        clauses.append("o.order_date < %s")
        params.append(end_date + timedelta(days=1))
    else:
        clauses.append("o.order_date < CURRENT_DATE + INTERVAL '1 day'")
    for column, value in (("ticker", ticker), ("client_id", client_id)):
        if value is not None:
            clauses.append(f"o.{column} = %s")
            params.append(value)
    if order_status is not None:
        if order_status.upper() in ("CANCELLED", "CANCELED"):
            clauses.append("UPPER(o.order_status) IN ('CANCELLED', 'CANCELED')")
        else:
            clauses.append("UPPER(o.order_status) = %s")
            params.append(order_status.upper())
    return " AND ".join(clauses), tuple(params)


def _report_rows(query, params):
    conn = get_warehouse_connection()
    try:
        df = pd.read_sql(query, conn, params=params)
        for column in ("period", "order_date"):
            if column in df:
                df[column] = df[column].astype(str)
        # JSON nulls rather than invalid NaN values.
        return df.astype(object).where(pd.notna(df), None).to_dict(orient='records')
    finally:
        conn.close()


def get_filtered_orders(limit=50, offset=0, **filters):
    conditions, params = _order_conditions(**filters)
    # One statement gives a consistent total, including pages beyond the last row.
    query = f"""
        WITH filtered AS (
            SELECT o.order_id, o.ticker, o.client_id, o.order_type,
                   o.order_status, o.price, o.quantity, o.order_date
            FROM orders o WHERE {conditions}
        ), page AS (
            SELECT * FROM filtered ORDER BY order_date DESC, order_id DESC
            LIMIT %s OFFSET %s
        )
        SELECT totals.total_orders, page.*
        FROM (SELECT COUNT(*) AS total_orders FROM filtered) totals
        LEFT JOIN page ON TRUE
        ORDER BY page.order_date DESC, page.order_id DESC
    """
    rows = _report_rows(query, params + (limit, offset))
    total = int(rows[0]['total_orders']) if rows else 0
    orders = [{key: value for key, value in row.items() if key != 'total_orders'}
              for row in rows if row['order_id'] is not None]
    return {'total_orders': total, 'orders': orders, 'limit': limit, 'offset': offset}


def get_trading_volume_metrics(**filters):
    """Notional turnover, not net cash flow; defaults to executed orders only."""
    filters.setdefault('order_status', 'FULFILLED')
    conditions, params = _order_conditions(**filters)
    return _report_rows(f"""
        SELECT COUNT(*) AS total_orders,
               COALESCE(SUM(o.quantity), 0) AS total_quantity,
               COALESCE(SUM(o.quantity * o.price), 0) AS total_trading_volume,
               COALESCE(SUM(o.quantity * o.price)
                   FILTER (WHERE UPPER(o.order_type) = 'BUY'), 0) AS buy_volume,
               COALESCE(SUM(o.quantity * o.price)
                   FILTER (WHERE UPPER(o.order_type) = 'SELL'), 0) AS sell_volume
        FROM orders o WHERE {conditions}
    """, params)[0]


def get_client_activity_trend(granularity='daily', **filters):
    units = {'daily': 'day', 'weekly': 'week', 'monthly': 'month'}
    unit = units[granularity]
    conditions, params = _order_conditions(**filters)
    return _report_rows(f"""
        SELECT DATE_TRUNC('{unit}', o.order_date)::DATE AS period,
               o.client_id, COUNT(*) AS trade_count,
               COALESCE(SUM(o.quantity * o.price), 0) AS total_volume,
               COUNT(DISTINCT o.ticker) AS instruments_traded
        FROM orders o WHERE {conditions}
        GROUP BY period, o.client_id ORDER BY period, o.client_id
    """, params)


def get_top_instruments(column = None, n = 10 ):
    # Top n instruments based on a specific column
    # Returns: DF --> JSON string
    if column is None:
        print("Column must be specified")
        return None
    conn = get_warehouse_connection()
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
    connection = get_warehouse_connection()
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
    conn = get_warehouse_connection()
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

def get_instrument_metrics(days=30, **filters):
    conn = get_warehouse_connection()
    try:
        conditions, params = _order_conditions(days=days, **filters)
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
            AND {conditions}
        GROUP BY i.ticker, i.asset_type
        ORDER BY total_volume DESC NULLS LAST
        """
        
        df = pd.read_sql(query, conn, params=params)
        
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

def get_timeseries_metrics(days=30, granularity='daily', **filters):
    conn = get_warehouse_connection()
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
        
        conditions, params = _order_conditions(days=days, **filters)
        query = f"""
        SELECT 
            {date_format} as period,
            COUNT(DISTINCT o.order_id) as trade_count,
            SUM(o.quantity * o.price) as total_volume,
            AVG(o.quantity * o.price) as avg_trade_value,
            COUNT(DISTINCT o.client_id) as active_clients,
            COUNT(DISTINCT o.ticker) as instruments_traded
        FROM orders o
        WHERE {conditions}
        GROUP BY period
        ORDER BY period ASC
        """
        
        df = pd.read_sql(query, conn, params=params)
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

def get_order_status_metrics(days=30, client_id=None):
    conn = get_warehouse_connection()
    try:
        query = """
        SELECT
            c.client_id,
            c.first_name,
            c.last_name,
            COUNT(o.order_id) AS total_orders,
            COUNT(o.order_id) FILTER (WHERE UPPER(o.order_status) = 'FULFILLED') AS fulfilled_orders,
            COUNT(o.order_id) FILTER (WHERE UPPER(o.order_status) = 'PENDING') AS pending_orders,
            COUNT(o.order_id) FILTER (WHERE UPPER(o.order_status) IN ('CANCELLED', 'CANCELED')) AS cancelled_orders
        FROM clients c
        LEFT JOIN orders o
            ON c.client_id = o.client_id
            AND o.order_date >= CURRENT_DATE - (%s * INTERVAL '1 day')
        """
        params = [days]

        if client_id is not None:
            query += " WHERE c.client_id = %s"
            params.append(client_id)

        query += """
        GROUP BY c.client_id, c.first_name, c.last_name
        ORDER BY c.client_id
        """

        df = pd.read_sql(query, conn, params=tuple(params)).fillna(0)
        numeric_cols = [
            'total_orders',
            'fulfilled_orders',
            'pending_orders',
            'cancelled_orders'
        ]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        return df.to_dict(orient='records')

    except Exception as e:
        print(f"Error fetching order status metrics: {e}")
        return None

    finally:
        conn.close()

def get_client_segments(days=30):
    conn = get_warehouse_connection()
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
    conn = get_warehouse_connection()
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