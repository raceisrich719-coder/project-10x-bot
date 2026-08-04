"""
Are there 'best days to trade' during the month? Test two documented patterns
on real SPY data, honestly:
  1. Day-of-week effect
  2. Turn-of-the-month effect (last trading day + first 3 of next month)

We report average returns, win rates, and a t-stat so we can tell a real signal
from random noise. A small difference with a low t-stat is NOISE, not an edge.
"""
from datetime import datetime
import numpy as np
from data import get_daily

# Pull as much history as Alpaca will give us.
px = get_daily("SPY", datetime(2000, 1, 1), datetime(2024, 12, 31))
ret = px["close"].pct_change().dropna()
print(f"SPY sample: {ret.index[0].date()} to {ret.index[-1].date()}  ({len(ret)} days)\n")

# ---- 1. Day of week ----
print("### Day-of-week average daily return ###")
names = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday"}
for dow in range(5):
    r = ret[ret.index.dayofweek == dow]
    print(f"  {names[dow]:<10} avg {r.mean()*100:+.3f}%   win {(r>0).mean()*100:4.1f}%   n={len(r)}")

# ---- 2. Turn of the month ----
# Mark first 3 and last 1 trading day of each month as the 'turn-of-month' window.
df = ret.to_frame("ret")
df["ym"] = df.index.to_period("M")
df["rank_from_start"] = df.groupby("ym").cumcount()
df["rank_from_end"] = df.groupby("ym").cumcount(ascending=False)
df["tom"] = (df["rank_from_start"] < 3) | (df["rank_from_end"] < 1)

tom = df.loc[df["tom"], "ret"]
rest = df.loc[~df["tom"], "ret"]

# Welch t-statistic: how many std errors apart are the two means?
t = (tom.mean() - rest.mean()) / np.sqrt(tom.var()/len(tom) + rest.var()/len(rest))

print("\n### Turn-of-the-month (last day + first 3) vs the rest ###")
print(f"  Turn-of-month days: avg {tom.mean()*100:+.3f}%   win {(tom>0).mean()*100:4.1f}%   n={len(tom)}")
print(f"  All other days:     avg {rest.mean()*100:+.3f}%   win {(rest>0).mean()*100:4.1f}%   n={len(rest)}")
print(f"  t-stat = {t:.2f}   (|t|>2 = probably real, <2 = likely noise)")

# How much of the total buy-and-hold gain happened on those few days?
tom_growth = (1 + tom).prod() - 1
rest_growth = (1 + rest).prod() - 1
print(f"\n  Compounded gain on turn-of-month days only: {tom_growth*100:+.0f}%  "
      f"({len(tom)} days, ~{len(tom)/len(ret)*100:.0f}% of all days)")
print(f"  Compounded gain on all other days:          {rest_growth*100:+.0f}%")
