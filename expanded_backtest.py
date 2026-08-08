"""
Expanded honest sweep: proven families + speculative ones, scored out-of-sample.
Special focus on the CORE SLEEVE candidate (vol-target + trend) since that's what
we're about to build. Same rule: only out-of-sample survival counts.
"""
from datetime import datetime
import numpy as np
import pandas as pd
import backtest as bt
from data import get_daily

ASSETS = ["SPY", "QQQ", "IWM", "DIA"]
SPLIT = pd.Timestamp("2021-01-01", tz="America/New_York")

specs = [("Buy&Hold", bt.buy_and_hold)]
for w in (100, 150, 200):
    specs.append((f"Trend>{w}d", lambda p, w=w: bt.price_above_sma(p, w)))
for lb in (100, 126, 200):
    specs.append((f"TSmom{lb}", lambda p, l=lb: bt.ts_momentum(p, l)))
for tv in (0.10, 0.15, 0.20):
    specs.append((f"VolTgt{int(tv*100)}", lambda p, t=tv: bt.vol_target(p, t, 20)))
for tv in (0.10, 0.15, 0.20):                       # the CORE candidate
    specs.append((f"VolTrend{int(tv*100)}", lambda p, t=tv: bt.vol_target_trend(p, t, 20, 200)))
for w in (20, 50, 100):                             # speculative breakout
    specs.append((f"Breakout{w}", lambda p, w=w: bt.donchian(p, w)))


def metrics(ret):
    if len(ret) < 30:
        return dict(cagr=0, dd=0, sharpe=0)
    eq = (1 + ret).cumprod()
    yrs = len(ret) / 252
    final = eq.iloc[-1]
    cagr = final ** (1 / yrs) - 1 if final > 0 else -1.0
    dd = (eq / eq.cummax() - 1).min()
    vol = ret.std() * np.sqrt(252)
    sharpe = (ret.mean() * 252) / vol if vol > 0 else 0.0
    return dict(cagr=cagr, dd=dd, sharpe=sharpe)


rows = []
cache = {a: get_daily(a, datetime(2015, 6, 1), datetime(2024, 12, 31)) for a in ASSETS}
for asset in ASSETS:
    prices = cache[asset]
    for name, fn in specs:
        ret = bt.run(prices, fn(prices), name)["returns"]
        m = metrics(ret[ret.index >= SPLIT])
        rows.append(dict(asset=asset, strat=name, oos_sharpe=m["sharpe"],
                         oos_cagr=m["cagr"], oos_dd=m["dd"]))

df = pd.DataFrame(rows)
print(f"\nRan {len(df)} backtests. Ranked by OUT-OF-SAMPLE risk-adjusted return.\n")

print("TOP 10 overall:")
print(f"{'asset':<6}{'strategy':<12}{'OOSsharpe':>10}{'OOScagr':>9}{'OOSdd':>7}")
for _, r in df.sort_values("oos_sharpe", ascending=False).head(10).iterrows():
    print(f"{r['asset']:<6}{r['strat']:<12}{r['oos_sharpe']:>10.2f}{r['oos_cagr']*100:>8.0f}%{r['oos_dd']*100:>6.0f}%")

print("\nCORE SLEEVE candidate (VolTrend = vol-target + 200d trend):")
core = df[df["strat"].str.startswith("VolTrend")].sort_values("oos_sharpe", ascending=False)
print(f"{'asset':<6}{'strategy':<12}{'OOSsharpe':>10}{'OOScagr':>9}{'OOSdd':>7}")
for _, r in core.iterrows():
    print(f"{r['asset']:<6}{r['strat']:<12}{r['oos_sharpe']:>10.2f}{r['oos_cagr']*100:>8.0f}%{r['oos_dd']*100:>6.0f}%")

bh = df[df["strat"] == "Buy&Hold"].set_index("asset")["oos_sharpe"]
print(f"\n(Buy&Hold OOS Sharpe for reference: " +
      ", ".join(f"{a} {bh[a]:.2f}" for a in ASSETS) + ")")
