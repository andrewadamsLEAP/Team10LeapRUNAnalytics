import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from shared.database_connections import get_warehouse_connection
from decimal import Decimal


def _average_cost(orders):
    """Moving weighted-average cost, excluding realized gains and fees."""
    quantity, cost = Decimal(0), Decimal(0)
    for order in orders:
        amount = Decimal(str(order['quantity']))
        price = Decimal(str(order['price']))
        side = str(order['order_type']).upper()
        if amount <= 0 or price < 0:
            return None, None
        if side == 'BUY':
            quantity += amount
            cost += amount * price
        elif side == 'SELL' and amount <= quantity:
            cost -= (cost / quantity) * amount
            quantity -= amount
        else:
            return None, None
    return quantity, (cost / quantity if quantity else None)


def get_client_holdings(client_id):
    """Value long holdings at latest available bid, with ask fallback.

    Prices are not FX converted. Asset values must use a common quote currency.
    Missing prices/history are disclosed rather than invented as zero profit.
    """
    conn = get_warehouse_connection()
    try:
        holdings = pd.read_sql("""
            SELECT h.ticker, h.quantity, i.asset_type,
                   COALESCE(p.bid_price, p.ask_price) AS current_price,
                   p.recorded_at AS price_timestamp
            FROM holdings h
            LEFT JOIN instruments i ON i.ticker = h.ticker
            LEFT JOIN LATERAL (
                SELECT bid_price, ask_price, recorded_at
                FROM prices WHERE ticker = h.ticker
                ORDER BY recorded_at DESC, price_id DESC LIMIT 1
            ) p ON TRUE
            WHERE h.client_id = %s AND h.quantity > 0
            ORDER BY h.ticker
        """, conn, params=(client_id,))
        orders = pd.read_sql("""
            SELECT ticker, quantity, price, order_type
            FROM orders WHERE client_id = %s AND UPPER(order_status) = 'FULFILLED'
            ORDER BY order_date, order_id
        """, conn, params=(client_id,))
    finally:
        conn.close()

    result = []
    for row in holdings.to_dict(orient='records'):
        quantity = Decimal(str(row['quantity']))
        price = (Decimal(str(row['current_price']))
                 if pd.notna(row['current_price']) else None)
        history = orders.loc[orders['ticker'] == row['ticker']].to_dict(orient='records')
        history_quantity, average = _average_cost(history)
        complete = history_quantity == quantity and average is not None
        value = quantity * price if price is not None else None
        gain = quantity * (price - average) if complete and price is not None else None
        asset_type = str(row['asset_type']).upper()
        ticker = str(row['ticker']).upper()
        # Bitcoin is a non-overlapping category, not counted again as crypto.
        if ticker in ('BTC', 'BTCUSD', 'BTC-USD', 'BTC/USD', 'XBT', 'BITCOIN') or asset_type == 'BITCOIN':
            category = 'bitcoin'
        elif asset_type in ('STOCK', 'STOCKS', 'EQUITY', 'EQUITIES'):
            category = 'stock'
        elif asset_type in ('CRYPTO', 'CRYPTOCURRENCY', 'CRYPTO_CURRENCY'):
            category = 'crypto'
        else:
            category = 'other'
        result.append({
            'ticker': row['ticker'], 'asset_type': row['asset_type'] if pd.notna(row['asset_type']) else None,
            'category': category, 'quantity': float(quantity),
            'current_price': float(price) if price is not None else None,
            'price_timestamp': str(row['price_timestamp']) if pd.notna(row['price_timestamp']) else None,
            'market_value': float(value) if value is not None else None,
            'average_cost': float(average) if complete else None,
            'unrealized_gain': float(gain) if gain is not None else None,
            'unrealized_gain_percentage': float((price - average) / average * 100)
                if complete and average and price is not None else None,
            'cost_basis_complete': complete,
        })
    return result


def get_top_client_holdings(client_id):
    holdings = get_client_holdings(client_id)
    ranked = [row for row in holdings if row['unrealized_gain'] is not None]
    ranked.sort(key=lambda row: (-row['unrealized_gain'], row['ticker']))
    return {
        'holdings': ranked[:5],
        'excluded_tickers': [row['ticker'] for row in holdings if row['unrealized_gain'] is None],
        'profit_method': 'unrealized moving weighted-average cost; excludes fees and FX',
    }


def get_client_allocation(client_id):
    holdings = get_client_holdings(client_id)
    values = {category: 0.0 for category in ('stock', 'crypto', 'bitcoin', 'other')}
    for holding in holdings:
        if holding['market_value'] is not None:
            values[holding['category']] += holding['market_value']
    total = sum(values.values())
    return {
        'total_market_value': total,
        'allocation': [
            {'category': category, 'market_value': value,
             'percentage': round(value / total * 100, 4) if total else 0.0}
            for category, value in values.items()
        ],
        'unpriced_tickers': [row['ticker'] for row in holdings if row['market_value'] is None],
        'valuation': 'latest bid with ask fallback; common quote currency required; excludes cash',
    }

def fetch_instruments_data():
    # Fetch all instruments from the database and return as JSON.
    # Returns: DF --> JSON string
    conn = get_warehouse_connection()
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
    conn = get_warehouse_connection()
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
    conn = get_warehouse_connection()
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
    conn = get_warehouse_connection()
    try:
        day_start = pd.Timestamp(quote_timestamp)
        if day_start.tzinfo is None:
            day_start = day_start.tz_localize('America/Chicago')
        day_start = day_start.normalize()
        day_end = day_start + pd.Timedelta(days=1)

        query = """
                SELECT *, recorded_at AS quote_timestamp
        FROM prices
        WHERE ticker = %s
                    AND recorded_at >= %s
                    AND recorded_at < %s
                ORDER BY recorded_at ASC, price_id ASC
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
    