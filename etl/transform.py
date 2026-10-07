import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone

def normalize_datetime(dt):
    """Normalize datetime to be timezone-aware (add UTC if naive)"""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def _normalize_rows(rows):
    """Normalize all datetimes (last column) in rows"""
    if not rows:
        return rows
    
    normalized = []
    for row in rows:
        # Convert row to list if it's a tuple
        row_list = list(row)
        # Normalize the last element (timestamp)
        if row_list:
            row_list[-1] = normalize_datetime(row_list[-1])
        normalized.append(tuple(row_list))
    return normalized


def transformClients(client_rows):
    """Normalize datetime in client rows"""
    return _normalize_rows(client_rows)


def transformEmployees(employee_rows):
    """Normalize datetime in employee rows"""
    return _normalize_rows(employee_rows)


def transformPrices(price_rows):
    """Normalize datetime in price rows"""
    return _normalize_rows(price_rows)


def transformTransactions(transaction_rows):
    """Normalize datetime in transaction rows"""
    return _normalize_rows(transaction_rows)


def transformHoldingsAndOrders(holdings_order_rows):
    """Normalize datetime in holdings and orders rows"""
    return _normalize_rows(holdings_order_rows)
