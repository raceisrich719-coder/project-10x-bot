"""
The bot's MEMORY -- permanent, never auto-erased. This is what makes it 'learn'
and what lets us analyze strategies months from now.

Every live trade is saved THREE ways in botmemory/:
  trades.jsonl   full-fidelity record, one JSON line per trade (for the bot to read)
  trades.csv     same data, spreadsheet-friendly (open in Excel to analyze)
  lessons.json   rolling distilled stats -- 'what I've learned' per symbol
Plus:
  equity.csv     a timestamped snapshot of account value over time (for charting)

Nothing here is wiped by the daily autopilot -- it only appends. The only eraser
is reset.py, and that now archives a backup first.
"""
import os
import csv
import json
from datetime import datetime

MEM_DIR = os.path.join(os.path.dirname(__file__), "botmemory")
TRADES = os.path.join(MEM_DIR, "trades.jsonl")
TRADES_CSV = os.path.join(MEM_DIR, "trades.csv")
EQUITY_CSV = os.path.join(MEM_DIR, "equity.csv")
LESSONS = os.path.join(MEM_DIR, "lessons.json")

CSV_FIELDS = ["ts", "action", "symbol", "qty", "price", "usd", "pnl", "reason"]


def _ensure():
    os.makedirs(MEM_DIR, exist_ok=True)


def record(event: dict) -> dict:
    """Append one trade event everywhere. Pass action/symbol/qty/price/usd/reason,
    and 'pnl' on exits so the bot can learn what worked."""
    _ensure()
    event = {"ts": datetime.now().isoformat(timespec="seconds"), **event}

    # 1. Full-fidelity JSON line.
    with open(TRADES, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    # 2. Spreadsheet-friendly CSV (write header once).
    new_file = not os.path.exists(TRADES_CSV)
    with open(TRADES_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerow({k: event.get(k, "") for k in CSV_FIELDS})

    _update_lessons()
    return event


def record_equity(equity: float, cash: float):
    """Snapshot account value over time so we can chart the whole journey."""
    _ensure()
    new_file = not os.path.exists(EQUITY_CSV)
    with open(EQUITY_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["ts", "equity", "cash"])
        w.writerow([datetime.now().isoformat(timespec="seconds"),
                    round(equity, 2), round(cash, 2)])


def load_trades() -> list:
    _ensure()
    if not os.path.exists(TRADES):
        return []
    with open(TRADES, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _update_lessons() -> dict:
    trades = load_trades()
    closed = [t for t in trades if t.get("pnl") not in (None, "")]
    lessons = {"total_events": len(trades), "closed_trades": len(closed),
               "updated": datetime.now().isoformat(timespec="seconds")}
    if closed:
        wins = [t for t in closed if t["pnl"] > 0]
        lessons["win_rate_pct"] = round(len(wins) / len(closed) * 100, 1)
        lessons["total_pnl"] = round(sum(t["pnl"] for t in closed), 2)
        lessons["avg_pnl"] = round(lessons["total_pnl"] / len(closed), 2)
        by_sym = {}
        for t in closed:
            by_sym.setdefault(t["symbol"], []).append(t["pnl"])
        lessons["by_symbol"] = {
            s: {"trades": len(p), "total_pnl": round(sum(p), 2),
                "avg_pnl": round(sum(p) / len(p), 2)}
            for s, p in sorted(by_sym.items())
        }
    with open(LESSONS, "w", encoding="utf-8") as f:
        json.dump(lessons, f, indent=2)
    return lessons


def lessons() -> dict:
    _ensure()
    if not os.path.exists(LESSONS):
        return {}
    with open(LESSONS, encoding="utf-8") as f:
        return json.load(f)


def symbol_bias(symbol: str) -> float:
    """What the bot has learned about a symbol: average P&L per past trade.
    Positive = it has worked for us. Used to lean toward proven setups."""
    return lessons().get("by_symbol", {}).get(symbol, {}).get("avg_pnl", 0.0)
