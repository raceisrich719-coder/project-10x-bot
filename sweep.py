"""
Strategy sweep: run every strategy family against the benchmark on several assets.
Honest, identical rules for all. The benchmark (buy & hold) is the bar to beat.
"""
from datetime import datetime
import backtest as bt
from data import get_daily

SYMBOLS = ["SPY", "QQQ"]
START = datetime(2015, 1, 1)
END = datetime(2024, 12, 31)

STRATEGIES = [
    ("Buy & Hold", bt.buy_and_hold),
    ("SMA 50/200 cross", lambda p: bt.sma_crossover(p, 50, 200)),
    ("Price > 200 SMA", lambda p: bt.price_above_sma(p, 200)),
    ("TS momentum 200d", lambda p: bt.ts_momentum(p, 200)),
    ("RSI(2) dip-buy", bt.rsi_mean_reversion),
    ("Vol target 15%", lambda p: bt.vol_target(p, 0.15, 20)),
]

for symbol in SYMBOLS:
    prices = get_daily(symbol, START, END)
    results = [bt.run(prices, fn(prices), name) for name, fn in STRATEGIES]
    print(f"\n=== {symbol}  {prices.index[0].date()} to {prices.index[-1].date()} "
          f"({len(prices)} days) ===\n")
    bt.print_comparison(results)
