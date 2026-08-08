"""
100+ backtests, done HONESTLY. The point isn't to cherry-pick winners -- it's to
show how many "winners" are just luck. Every strategy is scored on:
  IN-SAMPLE  2016-2020  (where we'd pick it)
  OUT-OF-SAMPLE 2021-2024 (data it never saw -- the real test)
A strategy only means something if its edge SURVIVES out-of-sample.

We report win rate (% of positive months) because Race asked -- but we JUDGE by
whether the edge holds up, because win rate alone is a vanity metric.
"""
from datetime import datetime
import numpy as np
import pandas as pd
import backtest as bt
from data import get_daily

ASSETS = ["SPY", "QQQ", "IWM", "DIA"]
SPLIT = pd.Timestamp("2021-01-01", tz="America/New_York")

# --- build ~28 strategy variants ---
specs = []
for fast in (10, 20, 50):
    for slow in (50, 100, 200):
        if fast < slow:
            specs.append((f"SMAx{fast}/{slow}", lambda p, f=fast, s=slow: bt.sma_crossover(p, f, s)))
for w in (20, 50, 100, 150, 200):
    specs.append((f"Trend>{w}d", lambda p, w=w: bt.price_above_sma(p, w)))
for lb in (20, 50, 100, 126, 200, 252):
    specs.append((f"TSmom{lb}", lambda p, l=lb: bt.ts_momentum(p, l)))
for tv in (0.08, 0.10, 0.12, 0.15, 0.20, 0.25):
    specs.append((f"VolTgt{int(tv*100)}", lambda p, t=tv: bt.vol_target(p, t, 20)))
for tr in (100, 150, 200):
    specs.append((f"RSI2dip{tr}", lambda p, t=tr: bt.rsi_mean_reversion(p, t)))


def metrics(ret):
    if len(ret) < 30:
        return dict(cagr=0, dd=0, sharpe=0, winrate=0)
    eq = (1 + ret).cumprod()
    yrs = len(ret) / 252
    final = eq.iloc[-1]
    cagr = final ** (1 / yrs) - 1 if final > 0 else -1.0
    dd = (eq / eq.cummax() - 1).min()
    vol = ret.std() * np.sqrt(252)
    sharpe = (ret.mean() * 252) / vol if vol > 0 else 0.0
    monthly = (1 + ret).groupby([ret.index.year, ret.index.month]).prod() - 1
    winrate = (monthly > 0).mean()
    return dict(cagr=cagr, dd=dd, sharpe=sharpe, winrate=winrate)


rows = []
prices_cache = {a: get_daily(a, datetime(2015, 6, 1), datetime(2024, 12, 31)) for a in ASSETS}
for asset in ASSETS:
    prices = prices_cache[asset]
    for name, fn in specs:
        ret = bt.run(prices, fn(prices), name)["returns"]
        is_r = ret[ret.index < SPLIT]
        oos_r = ret[ret.index >= SPLIT]
        m_is, m_oos = metrics(is_r), metrics(oos_r)
        rows.append(dict(asset=asset, strat=name,
                         is_win=m_is["winrate"], is_sharpe=m_is["sharpe"],
                         oos_win=m_oos["winrate"], oos_sharpe=m_oos["sharpe"],
                         oos_cagr=m_oos["cagr"], oos_dd=m_oos["dd"]))

df = pd.DataFrame(rows)
print(f"\nRan {len(df)} backtests ({len(specs)} strategies x {len(ASSETS)} assets)\n")

# Race's exact ask: strategies with >70% win rate in-sample
winners_is = df[df["is_win"] > 0.70]
print(f"Hit >70% win rate IN-SAMPLE (where we'd pick them):   {len(winners_is)} of {len(df)}")

# how many of THOSE still clear 70% out-of-sample?
survivors = winners_is[winners_is["oos_win"] > 0.70]
print(f"...of those, still >70% win rate OUT-OF-SAMPLE:        {len(survivors)}")
still_profitable = winners_is[winners_is["oos_sharpe"] > 0]
print(f"...of those, even just PROFITABLE out-of-sample:       {len(still_profitable)} "
      f"({len(still_profitable)/max(len(winners_is),1)*100:.0f}%)")

print("\nTop 8 by OUT-OF-SAMPLE risk-adjusted return (the honest ranking):")
top = df.sort_values("oos_sharpe", ascending=False).head(8)
print(f"{'asset':<6}{'strategy':<12}{'ISwin':>7}{'OOSwin':>8}{'OOSsharpe':>10}{'OOScagr':>9}{'OOSdd':>7}")
for _, r in top.iterrows():
    print(f"{r['asset']:<6}{r['strat']:<12}{r['is_win']*100:>6.0f}%{r['oos_win']*100:>7.0f}%"
          f"{r['oos_sharpe']:>10.2f}{r['oos_cagr']*100:>8.0f}%{r['oos_dd']*100:>6.0f}%")
