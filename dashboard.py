import streamlit as st
import pandas as pd
from python_sql_connection import get_connection

st.set_page_config(page_title="Trading Analytics", layout="wide")
st.title("Analytics Dashboard")

conn = get_connection()


try:
    trades_query = "SELECT COUNT(*) as total_trades FROM transactions"
    total_trades = pd.read_sql(trades_query, conn)['total_trades'][0]
    
    volume_query = "SELECT SUM(volume) as total_volume FROM transactions"
    total_volume = pd.read_sql(volume_query, conn)['total_volume'][0]
    
    average_query = "SELECT AVG(volume) as average_volume FROM transactions"
    average_volume = pd.read_sql(average_query, conn)['average_volume'][0]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Trades", total_trades)
    with col2:
        st.metric("Total Volume", total_volume)
    with col3:
        st.metric("Average Volume", average_volume)

finally:
    conn.close()