"""
Data test: pull historical daily bars for SPY from Alpaca.
Read-only. Confirms we have the raw material to backtest on.
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()
key = os.getenv("APCA_API_KEY_ID")
secret = os.getenv("APCA_API_SECRET_KEY")

client = StockHistoricalDataClient(key, secret)

req = StockBarsRequest(
    symbol_or_symbols="SPY",
    timeframe=TimeFrame.Day,
    start=datetime(2018, 1, 1),
    end=datetime(2024, 12, 31),
)

bars = client.get_stock_bars(req).df

print(f"Pulled {len(bars)} daily bars for SPY")
print(f"Date range: {bars.index.get_level_values('timestamp').min().date()} "
      f"to {bars.index.get_level_values('timestamp').max().date()}")
print()
print("First few rows:")
print(bars[["open", "high", "low", "close", "volume"]].head())
print()
print("Last few rows:")
print(bars[["open", "high", "low", "close", "volume"]].tail())
