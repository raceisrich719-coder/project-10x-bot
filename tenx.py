"""
PROJECT 10X -- paper-money sandbox. Goal: $100K -> $1M. Fake money, pure fun.
First weapon: TQQQ, a 3x-leveraged Nasdaq ETF. Triple the up, triple the down.
"""
from datetime import datetime
import backtest as bt
from data import get_daily

START, END = datetime(2016, 1, 1), datetime(2024, 12, 31)
CASH = 100_000
TARGET = 1_000_000

prices = get_daily("TQQQ", START, END)

plays = [
    ("TQQQ buy & hold (raw)", bt.buy_and_hold),
    ("TQQQ trend-timed 200d", lambda p: bt.price_above_sma(p, 200)),
    ("TQQQ vol-target 40%", lambda p: bt.vol_target(p, 0.40, 20)),
]

print(f"\nPROJECT 10X  |  start ${CASH:,}  ->  target ${TARGET:,}")
print(f"TQQQ {prices.index[0].date()} to {prices.index[-1].date()}\n")
print(f"{'Play':<26}{'Final $':>14}{'Multiple':>10}{'MaxDD':>8}  Hit $1M?")
print("-" * 72)
for name, fn in plays:
    res = bt.run(prices, fn(prices), name)
    m = bt.metrics(res)
    mult = res["equity"].iloc[-1]
    final = CASH * mult
    peak = CASH * res["equity"].cummax().iloc[-1]
    hit = "YES <== 10x!" if final >= TARGET else "no"
    print(f"{name:<26}{final:>14,.0f}{mult:>9.1f}x{m['max_drawdown']*100:>7.0f}%  {hit}")

print("\nMaxDD = the worst peak-to-trough gut-punch along the way. Watch that column.")
