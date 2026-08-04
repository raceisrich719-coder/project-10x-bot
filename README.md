# Project 10X

A paper-money trading bot — a for-fun challenge to grow a $100,000 Alpaca **paper**
account toward $1,000,000. Fake money, real market data. Aggressive on purpose.

## How the bot works
- `intraday_bot.py` — scans a universe of fast movers (leveraged ETFs + megacaps),
  rides short-term momentum, takes profit at +1.5%, stops out at -1%, reacts to
  live news, and rotates. Runs one cycle per call.
- `run_day.py` — the all-day autopilot: runs a cycle every 3 minutes during market
  hours, then generates a report and pushes data here.
- `journal.py` + `botmemory/` — permanent trade memory (never auto-wiped).
- `report.py` — end-of-day earnings report.

## Where the data lives (for daily analysis)
- `botmemory/trades.csv` — every trade: ts, action, symbol, qty, price, usd, pnl, reason
- `botmemory/trades.jsonl` — same, full fidelity
- `botmemory/equity.csv` — account value over time
- `botmemory/lessons.json` — rolling per-symbol win rate / avg P&L
- `reports/YYYY-MM-DD.txt` — daily earnings reports
- `research/` — where the daily cloud analysis writes its findings

## Daily research job
A scheduled cloud agent analyzes the accumulated data each weekday after close,
looking for what's working vs. bleeding, and proposes concrete tuning to make the
bot smarter over time. See `research/` for its output.
