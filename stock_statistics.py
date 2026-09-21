import pandas as pd
from python_sql_connection import get_connection
from decimal import Decimal

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
        
def fetch_prices_data():
    # Fetch all prices from the database and return as JSON.
    # Returns: DF --> JSON string
    conn = get_connection()
    try:
        query = """
        SELECT * 
        FROM prices
        """
        
        df = pd.read_sql(query, conn)
        print(f"Fetched {len(df)} prices")
        return df.to_json(orient='records')
    
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return None
        
    finally:
        conn.close()
        
def fetch_prices_by_ticker_and_date(ticker: str, quote_timestamp: pd.Timestamp):
    # Fetch all prices table data for the day and ticker from the database and return as JSON.
    # Returns: DF --> JSON string
    conn = get_connection()
    try:
        day_start = pd.Timestamp(quote_timestamp)
        if day_start.tzinfo is None:
            day_start = day_start.tz_localize('America/Chicago')
        day_start = day_start.normalize()
        day_end = day_start + pd.Timedelta(days=1)

        query = """
        SELECT *
        FROM prices
        WHERE ticker = %s
          AND quote_timestamp >= %s
          AND quote_timestamp < %s
        ORDER BY quote_timestamp ASC
        """
        df = pd.read_sql(query, conn, params=(ticker, day_start, day_end))
        return df

    except Exception as e:
        print(f"Error fetching prices: {e}")
        return None

    finally:
        conn.close()
            
def find_open(prices_df: pd.DataFrame): 
    try:
        prices_df = prices_df.copy()
        # Sort by timestamp
        prices_df['quote_timestamp'] = pd.to_datetime(prices_df['quote_timestamp'])
        # Get the first price put in for that day
        first_price = prices_df.sort_values('quote_timestamp').iloc[0]['ask_price']
        return first_price
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error finding open price: {e}")
        return None

def find_close(prices_df: pd.DataFrame): 
    try:
        prices_df = prices_df.copy()
        # Sort by timestamp
        prices_df['quote_timestamp'] = pd.to_datetime(prices_df['quote_timestamp'])
        # Get the last price of the day and put in for that day
        last_price = prices_df.sort_values('quote_timestamp').iloc[-1]['ask_price']
        return last_price
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error finding close price: {e}")
        return None

# Returns most recent tuple of what buyer is willing to buy for (price) and size
def find_last_bid_price_and_size_of_day(prices_df: pd.DataFrame):
    try:
        prices_df = prices_df.copy()
        prices_df['quote_timestamp'] = pd.to_datetime(prices_df['quote_timestamp'])
        # Get the last bid price of the day and put in for that day
        last_row = prices_df.sort_values('quote_timestamp').iloc[-1]
        # if you look on yahoo finance, it will be formatted bid_price x bid_size
        return (last_row['bid_price'], last_row['bid_size'])
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error finding bid price and size: {e}")
        return (None, None)

# Returns most recent tuple of what seller is willing to sell for (price) and size
def find_last_ask_price_and_size_of_day(prices_df: pd.DataFrame):
    try:
        prices_df = prices_df.copy()
        prices_df['quote_timestamp'] = pd.to_datetime(prices_df['quote_timestamp'])
        # Get the last ask price of the day and put in for that day
        last_row = prices_df.sort_values('quote_timestamp').iloc[-1]
        # if you look on yahoo finance, it will be formatted ask_price x ask_size
        return (last_row['ask_price'], last_row['ask_size'])
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error finding ask price and size: {e}")
        return (None, None)

# Returns tuple of lowest price and highest price for given day.
def find_day_range(prices_df: pd.DataFrame):
    try:
        prices_df = prices_df.copy()
        lowest = prices_df['ask_price'].min()
        highest = prices_df['ask_price'].max()
        return (lowest, highest)
    except (KeyError, ValueError) as e:
        print(f"Error finding day range: {e}")
        return (None, None)

# TODO: PE_RATIO AND EPS
    
def calculate_stock_metrics(ticker: str):
    tz = 'America/Chicago'
    today = pd.Timestamp.now(tz).normalize()
    yesterday = today - pd.Timedelta(days=1)

    today_prices = fetch_prices_by_ticker_and_date(ticker, today)
    yesterday_prices = fetch_prices_by_ticker_and_date(ticker, yesterday)
    
    if today_prices is None or today_prices.empty:
        return None
    
    prev_close = None
    if yesterday_prices is not None and not yesterday_prices.empty:
        prev_close = find_close(yesterday_prices)
    
    open_price = find_open(today_prices)
    bid_price, bid_size = find_last_bid_price_and_size_of_day(today_prices)
    ask_price, ask_size = find_last_ask_price_and_size_of_day(today_prices)
    day_low, day_high = find_day_range(today_prices)
    
    metrics = {
        'ticker': ticker,
        'open': float(open_price) if open_price else None,
        'prev_close': float(prev_close) if prev_close else None,
        'bid_price': float(bid_price) if bid_price else None,
        'bid_size': int(bid_size) if bid_size else None,
        'ask_price': float(ask_price) if ask_price else None,
        'ask_size': int(ask_size) if ask_size else None,
        'day_low': float(day_low) if day_low else None,
        'day_high': float(day_high) if day_high else None,
    }
    
    return metrics
    