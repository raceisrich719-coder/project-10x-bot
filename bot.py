"""
PROJECT 10X -- live paper bot, v1.
Strategy: trend-timed leveraged ETF. Hold TQQQ while it's above its 200-day
average (uptrend); go to cash when it drops below. Aggressive but rule-based --
this is the version that made 20x with 'only' a 50% drawdown in backtest.

Run:
    python bot.py          -> DRY RUN: shows exactly what it would do, trades nothing
    python bot.py --live   -> actually places PAPER orders on your Alpaca paper account

Fake money only -- TradingClient is pinned to paper=True.
"""
import os
import sys
import math
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from data import get_daily

SYMBOL = "TQQQ"
SMA_WINDOW = 200
TARGET_WEIGHT = 1.0          # 1.0 = deploy all cash when in-trend (no margin yet)
LIVE = "--live" in sys.argv

load_dotenv()
client = TradingClient(os.getenv("APCA_API_KEY_ID"),
                       os.getenv("APCA_API_SECRET_KEY"), paper=True)


def log(msg):
    os.makedirs("logs", exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line)
    with open("logs/bot.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    log("=" * 60)
    log(f"PROJECT 10X bot run  ({'LIVE' if LIVE else 'DRY RUN'})")

    # --- 1. Compute the signal ---
    bars = get_daily(SYMBOL, datetime.now() - timedelta(days=420), datetime.now())
    price = bars["close"].iloc[-1]
    sma = bars["close"].rolling(SMA_WINDOW).mean().iloc[-1]
    in_trend = price > sma
    log(f"{SYMBOL}: last ${price:.2f} | 200d SMA ${sma:.2f} | "
        f"{'UPTREND -> hold' if in_trend else 'DOWNTREND -> cash'}")

    # --- 2. Where we stand ---
    acct = client.get_account()
    equity = float(acct.portfolio_value)
    log(f"Equity ${equity:,.2f}  ({equity / 1_000_000 * 100:.1f}% of the $1M goal)")

    try:
        cur_qty = float(client.get_open_position(SYMBOL).qty)
    except Exception:
        cur_qty = 0.0

    # --- 3. Decide the trade ---
    target_dollars = equity * TARGET_WEIGHT if in_trend else 0.0
    target_qty = math.floor(target_dollars / price)
    delta = int(target_qty - cur_qty)
    log(f"{SYMBOL} position: have {cur_qty:.0f} -> want {target_qty:.0f} (delta {delta:+d})")

    if abs(delta) < 1:
        log("Already where we want to be. No trade.")
        return

    side = OrderSide.BUY if delta > 0 else OrderSide.SELL
    qty = abs(delta)
    approx = qty * price

    if not LIVE:
        log(f"DRY RUN: would {side.value.upper()} {qty} {SYMBOL} (~${approx:,.0f}). "
            f"Add --live to fire it.")
        return

    order = client.submit_order(
        MarketOrderRequest(symbol=SYMBOL, qty=qty, side=side, time_in_force=TimeInForce.DAY))
    log(f"LIVE: submitted {side.value.upper()} {qty} {SYMBOL} -> order {order.id}, status {order.status}")


if __name__ == "__main__":
    main()
