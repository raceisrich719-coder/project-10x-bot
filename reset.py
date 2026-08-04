"""
Reset the game to a clean slate: cancel open orders, liquidate all positions,
and archive+clear the bot's memory. (Can't reset the $100k without a fresh key.)

SAFE BY DESIGN: it copies all memory into a timestamped backup folder BEFORE
clearing, and makes you type YES first. Your trade history is never truly lost.

Run:  python reset.py
"""
import os
import glob
import shutil
from datetime import datetime
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

MEM_DIR = os.path.join(os.path.dirname(__file__), "botmemory")

confirm = input("This liquidates positions and clears memory (a backup is kept).\n"
                "Type YES to proceed: ").strip()
if confirm != "YES":
    print("Cancelled. Nothing changed.")
    raise SystemExit(0)

load_dotenv()
client = TradingClient(os.getenv("APCA_API_KEY_ID"),
                       os.getenv("APCA_API_SECRET_KEY"), paper=True)

# 1. Archive current memory first.
files = glob.glob(os.path.join(MEM_DIR, "*.*"))
if files:
    backup = os.path.join(MEM_DIR, "archive", f"backup_{datetime.now():%Y%m%d_%H%M%S}")
    os.makedirs(backup, exist_ok=True)
    for f in files:
        shutil.copy2(f, backup)
    print(f"Backed up {len(files)} memory file(s) -> {backup}")

print("Cancelling open orders...")
try:
    client.cancel_orders()
except Exception as e:
    print("  (nothing to cancel:", type(e).__name__, e, ")")

print("Liquidating all positions...")
try:
    client.close_all_positions(cancel_orders=True)
except Exception as e:
    print("  (nothing to liquidate:", type(e).__name__, e, ")")

print("Clearing active memory (backup retained)...")
for f in files:
    os.remove(f)

print("Clean slate. Ready for a fresh run.")
