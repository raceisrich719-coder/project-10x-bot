"""
PROJECT 10X -- the all-day autopilot.
Launch this in the morning and leave it. It waits for the open, then runs the
intraday brain every few minutes until the close, then fires the earnings report.

Run:
    python run_day.py          -> DRY RUN all day (logs decisions, trades nothing)
    python run_day.py --live   -> trades the PAPER account all day for real
"""
import sys
import time
from datetime import datetime

from intraday_bot import run_cycle, trade_client, LIVE
import report

INTERVAL = 180  # seconds between cycles (180s ~= up to 130 cycles/day)


def main():
    print(f"PROJECT 10X autopilot starting  ({'LIVE' if LIVE else 'DRY RUN'})  "
          f"cycle every {INTERVAL}s")
    ran_any = False

    while True:
        clock = trade_client.get_clock()
        if clock.is_open:
            try:
                run_cycle()
                ran_any = True
            except Exception as e:
                print(f"  cycle error ({type(e).__name__}: {e}) -- skipping this one")
            time.sleep(INTERVAL)
        else:
            if ran_any:
                print("\nMarket closed. Generating end-of-day report...")
                report.generate()
                print("Autopilot done for the day.")
                return
            # Pre-open: wait for the bell.
            nxt = clock.next_open
            print(f"{datetime.now():%H:%M:%S}  market closed, next open {nxt}. waiting...")
            time.sleep(60)


if __name__ == "__main__":
    main()
