from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from analytics import fetch_instruments_data

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/analytics/instruments")
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
  
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)