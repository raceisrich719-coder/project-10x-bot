"""
PROJECT 10X -- intraday trading brain. ONE cycle per call; the day loop
(run_day.py) calls it every few minutes during market hours.

Each cycle:
  1. Manage open positions -> take profits, cut losses (this is where most
     trades come from -> lots of learning data).
  2. Scan a universe of fast movers for fresh momentum, boosted by live news
     and by what the bot has LEARNED works (journal.symbol_bias).
  3. Rotate freed-up cash into the best new setups.
Every entry and exit is written to the bot's memory (journal.py).

Run:
    python intraday_bot.py          -> DRY RUN (decides + logs intent, trades nothing)
    python intraday_bot.py --live   -> places PAPER orders
"""
import os
import sys
import math
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest
from alpaca.data.enums import DataFeed

import journal
from data import get_minutes, get_daily

# ---- knobs (aggressive, on purpose -- it's a sandbox) ----
UNIVERSE = ["TQQQ", "SQQQ", "SOXL", "SOXS", "SPXL", "TSLA", "NVDA", "AMD", "META", "AAPL"]
TRADE_SIZE = 5_000        # $ per new position -> small clips, many trades
MAX_POSITIONS = 6         # how many names to hold at once
TAKE_PROFIT = 0.015       # +1.5% -> ring the register
STOP_LOSS = -0.010        # -1.0% -> cut it
MOMENTUM_LOOKBACK = 15    # minutes
INVERSE = {"SQQQ", "SOXS"}   # bearish/inverse ETFs -- never buy these (don't fight the uptrend)
COOLDOWN_SEC = 1800          # 30 min: don't re-buy a name right after selling it (kills churn)
LIVE = "--live" in sys.argv

_last_exit = {}              # symbol -> last sell time, powers the cooldown

load_dotenv()
_key, _secret = os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
trade_client = TradingClient(_key, _secret, paper=True)
news_client = NewsClient(_key, _secret)


def _order(symbol, qty, side, reason, price=None, pnl=None):
    """Place (or dry-run) a market order and journal it with full detail."""
    qty = int(qty)
    if qty < 1:
        return
    tag = "LIVE" if LIVE else "DRY"
    print(f"  [{tag}] {side.value.upper()} {qty} {symbol}  <- {reason}")
    if side == OrderSide.SELL:
        _last_exit[symbol] = time.time()      # start the anti-churn cooldown on this name
    if LIVE:
        trade_client.submit_order(MarketOrderRequest(
            symbol=symbol, qty=qty, side=side, time_in_force=TimeInForce.DAY))
        # Only real trades go into the bot's memory -- dry runs don't pollute learning.
        journal.record({"action": side.value.upper(), "symbol": symbol, "qty": qty,
                        "price": round(price, 2) if price else None,
                        "usd": round(qty * price, 2) if price else None,
                        "reason": reason, "pnl": pnl})


def _news_symbols():
    """Symbols in our universe that have fresh news right now (a catalyst)."""
    try:
        resp = news_client.get_news(NewsRequest(symbols=",".join(UNIVERSE), limit=20))
        items = resp.data.get("news", []) if hasattr(resp, "data") else []
        hot = set()
        for n in items:
            for s in (getattr(n, "symbols", []) or []):
                if s in UNIVERSE:
                    hot.add(s)
        return hot
    except Exception as e:
        print("  (news unavailable:", type(e).__name__, e, ")")
        return set()


def _momentum_scores():
    """Rank universe by recent minute-bar momentum. Empty when market is closed."""
    scores = {}
    try:
        df = get_minutes(UNIVERSE, lookback_min=MOMENTUM_LOOKBACK + 5)
    except Exception as e:
        print("  (intraday data unavailable:", type(e).__name__, e, ")")
        return scores
    if df is None or len(df) == 0:
        return scores
    for sym in UNIVERSE:
        try:
            closes = df.loc[sym]["close"]
        except KeyError:
            continue
        if len(closes) < 2:
            continue
        mom = closes.iloc[-1] / closes.iloc[0] - 1.0
        scores[sym] = mom
    return scores


REGIME_SYMBOL = "SPY"   # read the broad market to decide how aggressive to be


def market_regime():
    """Set aggression from the broad market's trend:
       1.0 = strong uptrend  -> go aggressive (full size, full positions)
       0.5 = mixed           -> play it safe (smaller size, fewer positions)
       0.0 = downtrend       -> defensive: manage exits only, NO new trades."""
    try:
        bars = get_daily(REGIME_SYMBOL, datetime.now() - timedelta(days=320), datetime.now(),
                         feed=DataFeed.IEX)
        close = bars["close"]
        price = close.iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        mom10 = price / close.iloc[-11] - 1.0
        if price > sma50 and price > sma200 and mom10 > 0:
            return 1.0, f"RISK-ON strong uptrend (SPY {mom10*100:+.1f}%/10d) -> AGGRESSIVE"
        if price > sma200:
            return 0.5, "NEUTRAL mixed trend -> cautious, smaller size"
        return 0.0, "RISK-OFF downtrend (SPY below its 200-day) -> defensive, no new trades"
    except Exception as e:
        print("  (regime check failed:", type(e).__name__, e, ")")
        return 0.5, "UNKNOWN -> cautious default"


def run_cycle():
    print("--- cycle ---")
    acct = trade_client.get_account()
    equity = float(acct.portfolio_value)
    cash = float(acct.cash)

    positions = {p.symbol: p for p in trade_client.get_all_positions()}

    # 1. Manage exits: take profits, cut losses.
    for sym, p in positions.items():
        plpc = float(p.unrealized_plpc)
        pl = float(p.unrealized_pl)
        cur_price = float(p.current_price)
        if plpc >= TAKE_PROFIT:
            _order(sym, float(p.qty), OrderSide.SELL,
                   f"take profit +{plpc*100:.1f}% (${pl:+,.0f})", price=cur_price, pnl=pl)
        elif plpc <= STOP_LOSS:
            _order(sym, float(p.qty), OrderSide.SELL,
                   f"stop loss {plpc*100:.1f}% (${pl:+,.0f})", price=cur_price, pnl=pl)

    # 2. Look for fresh entries -- but only as aggressively as the market allows.
    regime_mult, regime_label = market_regime()
    print(f"  Market regime: {regime_label}")

    max_pos = {1.0: MAX_POSITIONS, 0.5: 3, 0.0: 0}.get(regime_mult, 3)
    eff_size = TRADE_SIZE * regime_mult      # smaller clips when cautious, none when defensive
    held = set(positions.keys())
    slots = max_pos - len(held)
    if slots > 0 and eff_size > 0 and cash > eff_size:
        scores = _momentum_scores()
        hot_news = _news_symbols()
        ranked = []
        for sym, mom in scores.items():
            if sym in held or sym in INVERSE:                 # skip held + never buy inverse ETFs
                continue
            if time.time() - _last_exit.get(sym, 0) < COOLDOWN_SEC:
                continue                                      # just traded this -- cool off, no churn
            score = mom + (0.002 if sym in hot_news else 0)   # news nudge
            score += journal.symbol_bias(sym) / 100000.0      # learned edge nudge
            ranked.append((score, mom, sym))
        ranked.sort(reverse=True)

        stance = "aggressive" if regime_mult >= 1 else "cautious"
        for score, mom, sym in ranked[:slots]:
            if mom <= 0:            # only buy things actually moving up
                continue
            price = None
            try:
                # last minute close as a price estimate
                df = get_minutes([sym], lookback_min=5)
                price = float(df.loc[sym]["close"].iloc[-1])
            except Exception:
                continue
            qty = math.floor(eff_size / price)
            catalyst = "news+" if sym in hot_news else ""
            _order(sym, qty, OrderSide.BUY,
                   f"{catalyst}momentum +{mom*100:.2f}% over {MOMENTUM_LOOKBACK}m [{stance}]",
                   price=price)

    # Snapshot account value each cycle -> a full equity history to chart later.
    if LIVE:
        journal.record_equity(equity, cash)

    l = journal.lessons()
    print(f"  equity ${equity:,.0f} | cash ${cash:,.0f} | positions {len(positions)} "
          f"| lifetime closed trades {l.get('closed_trades', 0)} "
          f"| win rate {l.get('win_rate_pct', 0)}%")


if __name__ == "__main__":
    # When invoked directly (e.g. from the cloud cron), only trade if the market
    # is actually open. --force overrides for testing.
    if "--force" in sys.argv or trade_client.get_clock().is_open:
        run_cycle()
    else:
        print("Market closed -- skipping cycle.")
