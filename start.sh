#!/bin/bash

echo "Starting Team10LeapRUNAnalytics..."

# Start ETL scheduler in the background
echo "Starting ETL scheduler..."
cd /app/etl
python main.py > /var/log/etl.log 2>&1 &
ETL_PID=$!
echo "ETL scheduler started (PID: $ETL_PID)"

# Start Analytics API (foreground - Docker will track this)
echo "Starting Analytics API on port 5000..."
cd /app/analytics_statistics
exec python -m uvicorn api:app --host 0.0.0.0 --port 5000
