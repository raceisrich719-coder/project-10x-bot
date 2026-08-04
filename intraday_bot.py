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
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest

import journal
from data import get_minutes

# ---- knobs (aggressive, on purpose -- it's a sandbox) ----
UNIVERSE = ["TQQQ", "SQQQ", "SOXL", "SOXS", "SPXL", "TSLA", "NVDA", "AMD", "META", "AAPL"]
TRADE_SIZE = 5_000        # $ per new position -> small clips, many trades
MAX_POSITIONS = 6         # how many names to hold at once
TAKE_PROFIT = 0.015       # +1.5% -> ring the register
STOP_LOSS = -0.010        # -1.0% -> cut it
MOMENTUM_LOOKBACK = 15    # minutes
LIVE = "--live" in sys.argv

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

    # 2. Look for fresh entries.
    held = set(positions.keys())
    slots = MAX_POSITIONS - len(held)
    if slots > 0 and cash > TRADE_SIZE:
        scores = _momentum_scores()
        hot_news = _news_symbols()
        ranked = []
        for sym, mom in scores.items():
            if sym in held:
                continue
            score = mom + (0.002 if sym in hot_news else 0)   # news nudge
            score += journal.symbol_bias(sym) / 100000.0      # learned edge nudge
            ranked.append((score, mom, sym))
        ranked.sort(reverse=True)

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
            qty = math.floor(TRADE_SIZE / price)
            catalyst = "news+" if sym in hot_news else ""
            _order(sym, qty, OrderSide.BUY,
                   f"{catalyst}momentum +{mom*100:.2f}% over {MOMENTUM_LOOKBACK}m",
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
