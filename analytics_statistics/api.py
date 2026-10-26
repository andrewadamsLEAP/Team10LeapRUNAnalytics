import sys
import os
from io import BytesIO
from datetime import date
from typing import Literal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import pandas as pd
try:
    from .stock_statistics import (fetch_instruments_data, fetch_user_transactions,
                                   calculate_stock_metrics, get_top_client_holdings,
                                   get_client_allocation)
    from .analytics import (get_kpi_metrics, get_instrument_metrics, get_timeseries_metrics,
                            get_order_status_metrics, get_client_segments, get_instrument_details,
                            get_filtered_orders, get_trading_volume_metrics, get_client_activity_trend)
except ImportError:
    from stock_statistics import (fetch_instruments_data, fetch_user_transactions,
                                  calculate_stock_metrics, get_top_client_holdings,
                                  get_client_allocation)
    from analytics import (get_kpi_metrics, get_instrument_metrics, get_timeseries_metrics,
                           get_order_status_metrics, get_client_segments, get_instrument_details,
                           get_filtered_orders, get_trading_volume_metrics, get_client_activity_trend)

app = FastAPI(
    title="Trading Analytics (internal Spring Boot service)",
    description="No authentication is performed here. Spring Boot must authorize every request, "
                "derive client IDs from its authenticated principal, and restrict employee reports "
                "to REPORTER/ADMIN. Do not expose this service directly to browsers or the internet."
)


def report_filters(
    days: int = Query(30, ge=1, le=3650),
    ticker: str | None = Query(None, min_length=1, max_length=40),
    client_id: int | None = Query(None, gt=0),
    start_date: date | None = None,
    end_date: date | None = None,
    order_status: Literal['FULFILLED', 'PENDING', 'CANCELLED', 'CANCELED'] | None = None,
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must not be after end_date")
    if end_date == date.max:
        raise HTTPException(status_code=400, detail="end_date is too large")
    return dict(days=days, ticker=ticker, client_id=client_id, start_date=start_date,
                end_date=end_date, order_status=order_status)


def png_response(figure):
    image = BytesIO()
    FigureCanvasAgg(figure).print_png(image)
    return Response(content=image.getvalue(), media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@app.middleware("http")
async def private_responses(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#http://localhost:5000/analytics/transactions/3

@app.get("/analytics/instruments/")
def get_instruments():
    try:
        data = fetch_instruments_data()
        if data:
            return {
                "status": "success",
                "data": data
            }
        else:
            raise HTTPException(status_code=404, detail="Instruments not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/analytics/transactions/{client_id}")
def get_transactions(client_id: int):
    try:
        data = fetch_user_transactions(client_id)
        if data:
            return {
                "status": "success",
                "data": data
            }
        else:
            raise HTTPException(status_code=404, detail="Transactions not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  
@app.get("/stock_statistics/{ticker}")
def get_stock_metrics(ticker: str):
    try:
        data = calculate_stock_metrics(ticker)
        if data:
            return {
                "status": "success",
                "data": data
            }
        else:
            raise HTTPException(status_code=404, detail="Stock metrics not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/analytics/")    
def get_analytics_overview(days: int = Query(30, ge=1, le=3650)):
    try:
        data = get_kpi_metrics(days=days)
        if data:
            return {
                "status": "success",
                "data": data,
                "period_days": days
            }
        else:
            raise HTTPException(status_code=404, detail="Analytics overview not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/by-instrument")
def get_instrument_analytics(
    filters: dict = Depends(report_filters),
    sort_by: Literal['trade_count', 'total_volume', 'total_quantity'] = 'total_volume',
    limit: int | None = Query(None, ge=1, le=1000),
):
    try:
        data = get_instrument_metrics(**filters)
        if data is not None:
            if filters['ticker']:
                data = [row for row in data if row['ticker'] == filters['ticker']]
            data.sort(key=lambda row: (-row[sort_by], row['ticker']))
            if limit is not None:
                data = data[:limit]
            return {
                "status": "success",
                "data": data,
                "period_days": filters['days'],
                "filters": filters,
                "sort_by": sort_by
            }
        else:
            raise HTTPException(status_code=404, detail="Instrument analytics not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/trends")
def get_analytics_trends(
    filters: dict = Depends(report_filters),
    granularity: Literal['daily', 'weekly', 'monthly'] = 'daily',
):
    try:
        if granularity not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="Granularity must be 'daily', 'weekly', or 'monthly'")
        
        data = get_timeseries_metrics(**filters, granularity=granularity)
        if data is not None:
            return {
                "status": "success",
                "data": data,
                "period_days": filters['days'],
                "filters": filters,
                "granularity": granularity
            }
        else:
            raise HTTPException(status_code=404, detail="Trend analytics not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/trends/graph")
def get_analytics_trends_graph(
    filters: dict = Depends(report_filters),
    granularity: str = "daily",
    metric: str = "total_volume"
):
    allowed_granularities = ["daily", "weekly", "monthly"]
    allowed_metrics = [
        "trade_count",
        "total_volume",
        "avg_trade_value",
        "active_clients",
        "instruments_traded"
    ]

    try:
        if granularity not in allowed_granularities:
            raise HTTPException(
                status_code=400,
                detail="Granularity must be 'daily', 'weekly', or 'monthly'"
            )
        if metric not in allowed_metrics:
            raise HTTPException(
                status_code=400,
                detail=f"Metric must be one of: {', '.join(allowed_metrics)}"
            )

        data = get_timeseries_metrics(**filters, granularity=granularity)
        if not data:
            raise HTTPException(status_code=404, detail="Trend analytics not found")

        frame = pd.DataFrame(data)
        frame["period"] = pd.to_datetime(frame["period"])

        figure = Figure(figsize=(10, 5), dpi=120)
        axis = figure.add_subplot(1, 1, 1)
        axis.plot(frame["period"], frame[metric], marker="o", linewidth=2)
        axis.set_title(f"{metric.replace('_', ' ').title()} Trend")
        axis.set_xlabel("Period")
        axis.set_ylabel(metric.replace("_", " ").title())
        axis.grid(True, alpha=0.3)
        figure.autofmt_xdate()

        return png_response(figure)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/by-client")
def get_client_analytics(days: int = Query(30, ge=1, le=3650)):
    try:
        data = get_client_segments(days=days)
        if data:
            return {
                "status": "success",
                "data": data,
                "period_days": days
            }
        else:
            raise HTTPException(status_code=404, detail="Client analytics not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/order-status")
def get_client_order_status(days: int = Query(30, ge=1, le=3650),
                            client_id: int | None = Query(None, gt=0)):
    try:
        data = get_order_status_metrics(days=days, client_id=client_id)
        if data is not None:
            return {
                "status": "success",
                "data": data,
                "period_days": days,
                "client_id": client_id
            }
        raise HTTPException(status_code=404, detail="Order status data not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/instrument/{ticker}")
def get_instrument_details_endpoint(ticker: str, days: int = Query(30, ge=1, le=3650)):
    try:
        data = get_instrument_details(ticker=ticker, days=days)
        if data:
            return {
                "status": "success",
                "data": data,
                "period_days": days
            }
        else:
            raise HTTPException(status_code=404, detail=f"No data found for ticker {ticker}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.get('/api/analytics/clients/{client_id}/holdings/top-gainers', tags=['Client account'])
def client_top_gainers(client_id: int = Path(..., gt=0)):
    """Spring Boot must set client_id from the signed-in client's identity."""
    return {'status': 'success', 'client_id': client_id,
            'data': get_top_client_holdings(client_id)}


@app.get('/api/analytics/clients/{client_id}/allocation', tags=['Client account'])
def client_allocation(client_id: int = Path(..., gt=0)):
    return {'status': 'success', 'client_id': client_id,
            'data': get_client_allocation(client_id)}


@app.get('/api/analytics/clients/{client_id}/allocation/graph', tags=['Client account'])
def client_allocation_graph(client_id: int = Path(..., gt=0)):
    data = get_client_allocation(client_id)
    slices = [row for row in data['allocation'] if row['market_value'] > 0]
    figure = Figure(figsize=(7, 5), dpi=120, layout='constrained')
    axis = figure.add_subplot(1, 1, 1)
    if slices:
        axis.pie([row['market_value'] for row in slices],
                 labels=[row['category'].replace('_', ' ').title() for row in slices],
                 autopct='%1.1f%%', startangle=90)
    else:
        axis.text(0.5, 0.5, 'No priced holdings', ha='center', va='center')
        axis.set_axis_off()
    title = 'Portfolio allocation by market value'
    if data['unpriced_tickers']:
        title += '\nUnpriced holdings excluded'
    axis.set_title(title)
    return png_response(figure)


@app.get('/api/analytics/clients/{client_id}/order-status/graph', tags=['Client account'])
def client_order_status_graph(client_id: int = Path(..., gt=0),
                              days: int = Query(30, ge=1, le=3650)):
    rows = get_order_status_metrics(days=days, client_id=client_id)
    if rows is None:
        raise HTTPException(status_code=503, detail='Order status data unavailable')
    if not rows:
        raise HTTPException(status_code=404, detail='Client not found')
    row = rows[0]
    counts = [row['cancelled_orders'], row['pending_orders'], row['fulfilled_orders']]
    figure = Figure(figsize=(7, 5), dpi=120, layout='constrained')
    axis = figure.add_subplot(1, 1, 1)
    bars = axis.bar(['Cancelled', 'Pending', 'Fulfilled'], counts,
                    color=['#ef4444', '#f59e0b', '#10b981'])
    axis.bar_label(bars, fmt='%d')
    axis.set_ylim(0, max(max(counts), 1) * 1.2)
    axis.yaxis.get_major_locator().set_params(integer=True)
    axis.set_ylabel('Number of orders')
    axis.set_title(f'Order status — last {days} days')
    return png_response(figure)


@app.get('/api/analytics/orders', tags=['Employee reports'])
def employee_orders(filters: dict = Depends(report_filters),
                    limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Spring Boot: REPORTER/ADMIN only. Filtered, paginated orders and total."""
    return {'status': 'success', 'filters': filters,
            'data': get_filtered_orders(limit=limit, offset=offset, **filters)}


@app.get('/api/analytics/trading-volume', tags=['Employee reports'])
def employee_trading_volume(filters: dict = Depends(report_filters)):
    # Executed turnover by default; callers can explicitly select another status.
    filters = dict(filters)
    filters['order_status'] = filters['order_status'] or 'FULFILLED'
    return {'status': 'success', 'filters': filters,
            'data': get_trading_volume_metrics(**filters)}


@app.get('/api/analytics/client-activity', tags=['Employee reports'])
def employee_client_activity(filters: dict = Depends(report_filters),
                             granularity: Literal['daily', 'weekly', 'monthly'] = 'daily'):
    return {'status': 'success', 'filters': filters, 'granularity': granularity,
            'data': get_client_activity_trend(granularity=granularity, **filters)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)