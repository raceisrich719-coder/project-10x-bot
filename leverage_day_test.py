"""
TEST (Race's idea): predict the day's direction, then hold a 3x LONG ETF (TQQQ)
on predicted-up days and a 3x INVERSE ETF (SQQQ) on predicted-down days.

Everything rides on whether the 'prediction' actually has edge. We can't backtest
'a few morning hours' without intraday history, so we use each day's full
OPEN->CLOSE return as the closest proxy -- if a signal can't beat a coin flip on
the full day, it won't on the morning either.
"""
from datetime import datetime
import numpy as np
import pandas as pd
from data import get_daily

START, END = datetime(2016, 1, 1), datetime(2024, 12, 31)
qqq = get_daily("QQQ", START, END)
tqqq = get_daily("TQQQ", START, END)
sqqq = get_daily("SQQQ", START, END)

df = pd.DataFrame({
    "tqqq_oc": tqqq["close"] / tqqq["open"] - 1,   # 3x-long, held open->close
    "sqqq_oc": sqqq["close"] / sqqq["open"] - 1,   # 3x-inverse, held open->close
    "up_day": (qqq["close"] > qqq["open"]).astype(bool),
}).dropna()

sma20 = qqq["close"].rolling(20).mean()
signals = {
    "Trend (QQQ>20d SMA)": (qqq["close"].shift(1) > sma20.shift(1)),
    "Momentum (yest. up)": (qqq["close"].shift(1) > qqq["close"].shift(2)),
    "Always predict UP":   pd.Series(True, index=qqq.index),
}


def stats(ret):
    eq = (1 + ret).cumprod()
    years = len(ret) / 252
    cagr = eq.iloc[-1] ** (1 / years) - 1
    maxdd = (eq / eq.cummax() - 1).min()
    return eq.iloc[-1], cagr, maxdd


print(f"\nDaily 3x directional test  {df.index[0].date()}..{df.index[-1].date()}  ({len(df)} days)\n")
print(f"{'Strategy':<26}{'Final':>9}{'CAGR':>8}{'MaxDD':>8}{'DirAcc':>8}")
print("-" * 59)

for name, sig in signals.items():
    pred = sig.reindex(df.index).fillna(True)
    ret = pd.Series(np.where(pred, df["tqqq_oc"], df["sqqq_oc"]), index=df.index)
    acc = (pred == df["up_day"]).mean()
    final, cagr, maxdd = stats(ret)
    print(f"{name:<26}{final:>8.2f}x{cagr*100:>7.0f}%{maxdd*100:>7.0f}%{acc*100:>7.0f}%")

# reference: just hold TQQQ open->close every day (no prediction)
final, cagr, maxdd = stats(df["tqqq_oc"])
print(f"{'(ref) always TQQQ':<26}{final:>8.2f}x{cagr*100:>7.0f}%{maxdd*100:>7.0f}%{'--':>8}")
print("\nDirAcc = how often the 'prediction' called the day right. ~50% = coin flip.")
