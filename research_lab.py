"""
RESEARCH LAB -- the bot's 'study every style' brain.

While the live intraday bot chases fast adrenaline trades, this studies the
SLOWER styles too and records what actually works:
  - Long-term (years):        buy & hold, trend filters, vol targeting
  - Position / quarter-term:  multi-month momentum (hold for months)
  - Swing (days-weeks):       short crossovers, mean-reversion
It backtests each on real history across several assets, compares every one to
the buy & hold benchmark, and appends the findings to a growing knowledge base.

Writes:
  research/knowledge_base.md     dated, human-readable 'what we've learned'
  research/strategy_results.csv  every result as data, to track over time

Run:  python research_lab.py
"""
import os
import csv
from datetime import datetime
import backtest as bt
from data import get_daily

START, END = datetime(2015, 1, 1), datetime(2024, 12, 31)
ASSETS = ["SPY", "QQQ", "TQQQ"]

# style label -> (strategy fn, typical holding period)
STYLES = [
    ("Long-term buy & hold", bt.buy_and_hold, "years"),
    ("Position momentum (126d / ~2 quarters)", lambda p: bt.ts_momentum(p, 126), "months"),
    ("Long-term trend filter (200d)", lambda p: bt.price_above_sma(p, 200), "weeks-months"),
    ("Swing crossover (20/50)", lambda p: bt.sma_crossover(p, 20, 50), "days-weeks"),
    ("Swing mean-reversion (RSI-2 dip)", bt.rsi_mean_reversion, "days"),
    ("Vol-targeted (15%)", lambda p: bt.vol_target(p, 0.15, 20), "dynamic"),
]


def main():
    rows = []
    sections = []

    for asset in ASSETS:
        prices = get_daily(asset, START, END)
        bench = bt.metrics(bt.run(prices, bt.buy_and_hold(prices), "bh"))
        lines = [f"### {asset}  ({prices.index[0].date()} to {prices.index[-1].date()})", ""]
        for label, fn, hold in STYLES:
            m = bt.metrics(bt.run(prices, fn(prices), label))
            verdict = "BEATS" if m["sharpe"] > bench["sharpe"] else "loses to"
            lines.append(
                f"- **{label}** _({hold})_: {m['total_return']*100:.0f}% total, "
                f"{m['cagr']*100:.1f}% CAGR, {m['max_drawdown']*100:.0f}% maxDD, "
                f"Sharpe {m['sharpe']:.2f} — {verdict} buy&hold on risk-adjusted return")
            rows.append([datetime.now().date().isoformat(), asset, label, hold,
                         round(m["total_return"], 4), round(m["cagr"], 4),
                         round(m["max_drawdown"], 4), round(m["sharpe"], 3), m["trades"]])
        sections.append("\n".join(lines))
        print(f"studied {asset}: {len(STYLES)} styles")

    os.makedirs("research", exist_ok=True)

    kb = os.path.join("research", "knowledge_base.md")
    first = not os.path.exists(kb)
    with open(kb, "a", encoding="utf-8") as f:
        if first:
            f.write("# Project 10X — Trading Styles Knowledge Base\n\n"
                    "A backtested study of every trading style, appended over time so the "
                    "bot understands the whole landscape — not just the fast intraday game.\n")
        f.write(f"\n\n## Research run {datetime.now():%Y-%m-%d %H:%M}\n\n")
        f.write("\n\n".join(sections) + "\n")

    csv_path = os.path.join("research", "strategy_results.csv")
    new_csv = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_csv:
            w.writerow(["date", "asset", "style", "holding", "total_return",
                        "cagr", "max_drawdown", "sharpe", "trades"])
        w.writerows(rows)

    print(f"\nWrote {len(rows)} results to {kb} and {csv_path}")


if __name__ == "__main__":
    main()
