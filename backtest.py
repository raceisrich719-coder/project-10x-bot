"""
Backtest engine + honest metrics.

A "strategy" is just a function: given a price DataFrame, return a Series of
target positions for each day, where 1.0 = fully long, 0.0 = in cash.
(No leverage: we cap at 1.0. No shorting yet.)

The engine applies the position to the NEXT day's return (you can't trade on a
price you haven't seen yet -- this avoids look-ahead cheating) and charges
slippage whenever the position changes.
"""
import numpy as np
import pandas as pd

SLIPPAGE_PER_SIDE = 0.0005  # 5 basis points per trade side; conservative for liquid ETFs
TRADING_DAYS = 252


def run(prices: pd.DataFrame, target_position: pd.Series, name: str):
    """Run a backtest. Returns a dict of metrics and the equity curve."""
    close = prices["close"]
    daily_ret = close.pct_change().fillna(0.0)

    # Shift positions forward one day: today's signal is acted on at tomorrow's open-ish.
    # This is the anti-look-ahead rule -- you trade AFTER you see the signal, not during.
    pos = target_position.reindex(prices.index).ffill().fillna(0.0).clip(0.0, 1.0)
    pos_effective = pos.shift(1).fillna(0.0)

    # Slippage cost each time the position changes.
    turnover = pos_effective.diff().abs().fillna(0.0)
    cost = turnover * SLIPPAGE_PER_SIDE

    strat_ret = pos_effective * daily_ret - cost
    equity = (1.0 + strat_ret).cumprod()

    return {"name": name, "equity": equity, "returns": strat_ret,
            "trades": int((turnover > 0).sum())}


def metrics(result: dict) -> dict:
    equity = result["equity"]
    ret = result["returns"]
    years = len(equity) / TRADING_DAYS
    total_return = equity.iloc[-1] - 1.0
    cagr = equity.iloc[-1] ** (1 / years) - 1.0 if years > 0 else 0.0

    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_dd = drawdown.min()

    vol = ret.std() * np.sqrt(TRADING_DAYS)
    sharpe = (ret.mean() * TRADING_DAYS) / vol if vol > 0 else 0.0

    return {
        "name": result["name"],
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "trades": result["trades"],
    }


def print_comparison(results: list):
    rows = [metrics(r) for r in results]
    print(f"{'Strategy':<24}{'TotalRet':>10}{'CAGR':>9}{'MaxDD':>9}{'Sharpe':>8}{'Trades':>8}")
    print("-" * 66)
    for m in rows:
        print(f"{m['name']:<24}{m['total_return']*100:>9.1f}%{m['cagr']*100:>8.1f}%"
              f"{m['max_drawdown']*100:>8.1f}%{m['sharpe']:>8.2f}{m['trades']:>8}")


# ---------------------------------------------------------------------------
# Strategies (each returns a target-position Series)
# ---------------------------------------------------------------------------

def buy_and_hold(prices: pd.DataFrame) -> pd.Series:
    """The benchmark. Always fully invested. This is what every bot must beat."""
    return pd.Series(1.0, index=prices.index)


def sma_crossover(prices: pd.DataFrame, fast: int = 50, slow: int = 200) -> pd.Series:
    """Classic 'golden cross': long when fast SMA is above slow SMA, else cash."""
    close = prices["close"]
    fast_ma = close.rolling(fast).mean()
    slow_ma = close.rolling(slow).mean()
    return (fast_ma > slow_ma).astype(float)


def price_above_sma(prices: pd.DataFrame, window: int = 200) -> pd.Series:
    """Trend filter (Meb Faber style): long when price is above its N-day average,
    else cash. Famous for sidestepping big crashes at the cost of some upside."""
    close = prices["close"]
    return (close > close.rolling(window).mean()).astype(float)


def ts_momentum(prices: pd.DataFrame, lookback: int = 200) -> pd.Series:
    """Time-series momentum: long when today's price is above where it was N days ago.
    One of the most academically supported effects across markets."""
    close = prices["close"]
    return (close > close.shift(lookback)).astype(float)


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def rsi_mean_reversion(prices: pd.DataFrame, trend: int = 200) -> pd.Series:
    """Connors-style dip buying: only in an uptrend (price > 200 SMA), go long when
    2-day RSI is very oversold (<10), exit when price closes above its 5-day average."""
    close = prices["close"]
    uptrend = close > close.rolling(trend).mean()
    rsi2 = _rsi(close, 2)
    sma5 = close.rolling(5).mean()

    pos = np.zeros(len(close))
    in_trade = False
    for i in range(len(close)):
        if in_trade:
            if close.iloc[i] > sma5.iloc[i]:
                in_trade = False
        else:
            if uptrend.iloc[i] and rsi2.iloc[i] < 10:
                in_trade = True
        pos[i] = 1.0 if in_trade else 0.0
    return pd.Series(pos, index=close.index)


def vol_target(prices: pd.DataFrame, target_vol: float = 0.15, window: int = 20) -> pd.Series:
    """Volatility targeting: size the position so risk stays near a target level.
    Calmer in turbulent markets, fuller in calm ones. Capped at 1.0 (no leverage)."""
    close = prices["close"]
    realized = close.pct_change().rolling(window).std() * np.sqrt(TRADING_DAYS)
    return (target_vol / realized).clip(0.0, 1.0)


if __name__ == "__main__":
    from datetime import datetime
    from data import get_daily

    prices = get_daily("SPY", datetime(2018, 1, 1), datetime(2024, 12, 31))

    results = [
        run(prices, buy_and_hold(prices), "Buy & Hold SPY"),
        run(prices, sma_crossover(prices, 50, 200), "SMA 50/200 crossover"),
    ]

    print(f"\nSPY, {prices.index[0].date()} to {prices.index[-1].date()}, "
          f"{len(prices)} trading days\n")
    print_comparison(results)
    print("\nReminder: TotalRet = total gain over the whole period. "
          "MaxDD = worst peak-to-trough drop (the pain). Sharpe = return per unit of risk.")
