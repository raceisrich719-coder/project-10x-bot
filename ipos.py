"""
IPO research feed -- upcoming IPOs from Nasdaq's public calendar (free, no key).
For STUDYING/testing IPO-day strategies. Runs where there's clean internet
(the VPS/cloud); may be blocked/rate-limited elsewhere.

Note: Alpaca can't buy IPOs at the offering price (no retail allocations), and
new tickers may not be tradable until after they start trading. Day-1 IPO buying
is historically negative-expectancy for retail -- treat any trading as a small,
data-gathering experiment, not an income strategy.

Run:  python ipos.py
"""
import json
import urllib.request
from datetime import datetime

TECH_HINTS = ("tech", "software", "ai", "data", "cloud", "cyber", "semiconductor",
              "digital", "internet", "platform", "robot", "chip", "quantum")


def upcoming_ipos(month=None):
    month = month or datetime.now().strftime("%Y-%m")
    url = f"https://api.nasdaq.com/api/ipo/calendar?date={month}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (research bot)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    up = (data.get("data") or {}).get("upcoming") or {}
    return (up.get("upcomingTable") or {}).get("rows") or []


if __name__ == "__main__":
    try:
        rows = upcoming_ipos()
        print(f"Upcoming IPOs this month: {len(rows)}\n")
        for x in rows:
            name = (x.get("companyName") or "?")
            tag = "  <-- possibly TECH" if any(h in name.lower() for h in TECH_HINTS) else ""
            print(f"  {(x.get('proposedTickerSymbol') or '?'):<7} {name[:42]:<42} "
                  f"exp {x.get('expectedPriceDate','?')}  ${x.get('proposedSharePrice','?')}{tag}")
    except Exception as e:
        print("ERROR:", type(e).__name__, e)
        print("(Nasdaq API needs clean internet + a browser User-Agent; runs on the VPS/cloud.)")
