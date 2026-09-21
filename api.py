from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from stock_statistics import fetch_instruments_data, fetch_user_transactions, calculate_stock_metrics

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
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)