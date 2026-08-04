"""
Robustness tests -- the two things that kill fake edges:
  1. TIME: does the edge hold in a later period it wasn't designed around?
  2. COSTS: does it survive higher, more realistic trading friction?

We focus on the two survivors from the sweep: vol targeting and the 200-day trend filter.
"""
from datetime import datetime
import backtest as bt
from data import get_daily

SURVIVORS = [
    ("Buy & Hold", bt.buy_and_hold),
    ("Price > 200 SMA", lambda p: bt.price_above_sma(p, 200)),
    ("Vol target 15%", lambda p: bt.vol_target(p, 0.15, 20)),
]

PERIODS = [
    ("EARLY 2016-2020", datetime(2015, 6, 1), datetime(2020, 12, 31)),
    ("LATER 2021-2024", datetime(2020, 6, 1), datetime(2024, 12, 31)),
]

print("########## TEST 1: does the edge hold across different time periods? ##########")
for symbol in ["SPY", "QQQ"]:
    for label, start, end in PERIODS:
        prices = get_daily(symbol, start, end)
        # Trim warmup so early rows with no signal don't distort the sub-period.
        prices = prices.iloc[210:]
        results = [bt.run(prices, fn(prices), name) for name, fn in SURVIVORS]
        print(f"\n--- {symbol}  {label}  ({prices.index[0].date()} to {prices.index[-1].date()}) ---")
        bt.print_comparison(results)

print("\n\n########## TEST 2: does vol targeting survive higher trading costs? ##########")
prices = get_daily("SPY", datetime(2015, 6, 1), datetime(2024, 12, 31)).iloc[210:]
original = bt.SLIPPAGE_PER_SIDE
for bps in [5, 15, 30]:
    bt.SLIPPAGE_PER_SIDE = bps / 10000.0
    results = [
        bt.run(prices, bt.buy_and_hold(prices), "Buy & Hold"),
        bt.run(prices, bt.vol_target(prices, 0.15, 20), "Vol target 15%"),
    ]
    print(f"\n--- SPY, slippage = {bps} bps per side ---")
    bt.print_comparison(results)
bt.SLIPPAGE_PER_SIDE = original
