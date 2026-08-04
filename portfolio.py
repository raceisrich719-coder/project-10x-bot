"""
Multi-asset test: does diversification + vol targeting beat single-asset investing
on a risk-adjusted basis? Assets: SPY (stocks), TLT (long bonds), GLD (gold).

Approach: inverse-volatility ("risk parity") weights so no single asset dominates
the risk, then a vol-target overlay scales total exposure (capped at 1.0 -- no
leverage; leftover sits in cash). Rebalanced daily, slippage charged on turnover.

Benchmarks: buy & hold SPY, and a static 60/40 SPY/TLT.
"""
from datetime import datetime
import numpy as np
import pandas as pd
import backtest as bt
from data import get_daily

START, END = datetime(2015, 1, 1), datetime(2024, 12, 31)
ASSETS = ["SPY", "TLT", "GLD"]

# Align all assets on common dates.
closes = {}
for sym in ASSETS:
    closes[sym] = get_daily(sym, START, END)["close"]
px = pd.DataFrame(closes).dropna()
rets = px.pct_change().fillna(0.0)


def result_from_returns(port_ret: pd.Series, turnover: pd.Series, name: str) -> dict:
    equity = (1.0 + port_ret).cumprod()
    return {"name": name, "equity": equity, "returns": port_ret,
            "trades": int((turnover > 0).sum())}


# --- Benchmark 1: buy & hold SPY ---
spy_bh = result_from_returns(rets["SPY"], pd.Series(0.0, index=rets.index), "Buy & Hold SPY")

# --- Benchmark 2: static 60/40 SPY/TLT, rebalanced daily ---
w6040 = pd.DataFrame({"SPY": 0.6, "TLT": 0.4, "GLD": 0.0}, index=rets.index)
eff6040 = w6040.shift(1).fillna(0.0)
ret6040 = (eff6040 * rets).sum(axis=1)
turn6040 = eff6040.diff().abs().sum(axis=1)
r6040 = result_from_returns(ret6040 - turn6040 * bt.SLIPPAGE_PER_SIDE, turn6040, "Static 60/40")

# --- Candidate: risk-parity + vol-target overlay ---
vol = rets.rolling(20).std() * np.sqrt(bt.TRADING_DAYS)
inv_vol = 1.0 / vol
rp_weights = inv_vol.div(inv_vol.sum(axis=1), axis=0)          # risk-parity, sums to 1
rp_ret_unscaled = (rp_weights.shift(1).fillna(0.0) * rets).sum(axis=1)

target_vol = 0.10
port_vol = rp_ret_unscaled.rolling(20).std() * np.sqrt(bt.TRADING_DAYS)
scale = (target_vol / port_vol).clip(0.0, 1.0).fillna(0.0)     # cap 1.0 -> no leverage
final_w = rp_weights.mul(scale, axis=0)

eff_w = final_w.shift(1).fillna(0.0)
port_ret_gross = (eff_w * rets).sum(axis=1)
turnover = eff_w.diff().abs().sum(axis=1)
cand = result_from_returns(port_ret_gross - turnover * bt.SLIPPAGE_PER_SIDE, turnover,
                           "RiskParity+VolTgt")

print(f"\nMulti-asset ({'/'.join(ASSETS)})  {px.index[0].date()} to {px.index[-1].date()} "
      f"({len(px)} days)\n")
bt.print_comparison([spy_bh, r6040, cand])
print("\nQuestion we're answering: can spreading risk across assets give a better "
      "return-per-unit-of-risk (Sharpe) and smaller drawdown than stocks alone?")
