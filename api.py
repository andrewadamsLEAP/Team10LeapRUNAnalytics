from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from stock_statistics import fetch_instruments_data, fetch_user_transactions, calculate_stock_metrics
from analytics import get_kpi_metrics, get_instrument_metrics, get_timeseries_metrics, get_client_segments, get_instrument_details

app = FastAPI()

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/analytics/")    
def get_analytics_overview(days: int = 30):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/by-instrument")
def get_instrument_analytics(days: int = 30):
    try:
        data = get_instrument_metrics(days=days)
        if data:
            return {
                "status": "success",
                "data": data,
                "period_days": days
            }
        else:
            raise HTTPException(status_code=404, detail="Instrument analytics not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/trends")
def get_analytics_trends(days: int = 30, granularity: str = "daily"):
    try:
        if granularity not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="Granularity must be 'daily', 'weekly', or 'monthly'")
        
        data = get_timeseries_metrics(days=days, granularity=granularity)
        if data:
            return {
                "status": "success",
                "data": data,
                "period_days": days,
                "granularity": granularity
            }
        else:
            raise HTTPException(status_code=404, detail="Trend analytics not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/by-client")
def get_client_analytics(days: int = 30):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/instrument/{ticker}")
def get_instrument_details_endpoint(ticker: str, days: int = 30):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)