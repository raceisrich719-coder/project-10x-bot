"""
Data helper: fetch clean historical daily bars from Alpaca as a simple DataFrame.
Shared by backtests and (later) the live paper bot.
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

load_dotenv()
_KEY = os.getenv("APCA_API_KEY_ID")
_SECRET = os.getenv("APCA_API_SECRET_KEY")
_client = StockHistoricalDataClient(_KEY, _SECRET)


def get_daily(symbol: str, start: datetime, end: datetime):
    """Return a DataFrame indexed by date with open/high/low/close/volume for one symbol."""
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        adjustment=Adjustment.ALL,  # split + dividend adjusted -- essential or splits fake huge crashes
    )
    df = _client.get_stock_bars(req).df
    # Drop the symbol level so we have a clean date-indexed frame.
    df = df.reset_index(level="symbol", drop=True)
    df.index = df.index.tz_convert("America/New_York").normalize()
    df.index.name = "date"
    return df[["open", "high", "low", "close", "volume"]]


def get_minutes(symbols, lookback_min: int = 60):
    """Recent 1-minute bars for one or more symbols (intraday momentum signals).
    Returns the raw multi-index DataFrame (symbol, timestamp). May be empty when
    the market is closed."""
    end = datetime.now()
    start = end - timedelta(minutes=lookback_min + 5)
    req = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Minute,
        start=start,
        end=end,
        adjustment=Adjustment.RAW,
    )
    return _client.get_stock_bars(req).df
