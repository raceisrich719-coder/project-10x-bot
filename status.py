"""
PROJECT 10X scoreboard. Run anytime to see where the game stands.
    python status.py
"""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

load_dotenv()
client = TradingClient(os.getenv("APCA_API_KEY_ID"),
                       os.getenv("APCA_API_SECRET_KEY"), paper=True)

acct = client.get_account()
equity = float(acct.portfolio_value)
start, goal = 100_000, 1_000_000

pct = equity / goal
filled = int(pct * 40)
bar = "#" * filled + "-" * (40 - filled)

print("\n" + "=" * 52)
print("           PROJECT 10X  --  SCOREBOARD")
print("=" * 52)
print(f"  Equity:      ${equity:,.2f}")
print(f"  Cash:        ${float(acct.cash):,.2f}")
print(f"  Total P&L:   ${equity - start:+,.2f}  ({(equity/start - 1)*100:+.1f}% since start)")
print(f"\n  $100K [{bar}] $1M")
print(f"  {pct*100:.1f}% of the way to a million\n")

positions = client.get_all_positions()
if positions:
    print("  Positions:")
    for p in positions:
        upl = float(p.unrealized_pl)
        print(f"    {p.symbol:<6} {float(p.qty):>8.0f} sh  "
              f"mkt ${float(p.market_value):>12,.0f}  "
              f"P&L ${upl:>+10,.0f} ({float(p.unrealized_plpc)*100:+.1f}%)")
else:
    print("  Positions: none (all cash)")

open_orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))
if open_orders:
    print("\n  Open / queued orders:")
    for o in open_orders:
        print(f"    {o.side.value.upper():<4} {o.qty} {o.symbol}  status={o.status.value}")
print("=" * 52 + "\n")
