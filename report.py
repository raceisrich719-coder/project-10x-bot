"""
PROJECT 10X -- end-of-day earnings report.
Prints here, saves to reports/, and emails you IF you've set up Gmail creds.

Email setup (optional, you do this once -- I never see the password):
  In .env add:
    GMAIL_ADDRESS=you@gmail.com
    GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx   # a Google 'App Password', not your login
    REPORT_TO=you@gmail.com
  (Google account -> Security -> 2-Step Verification -> App passwords.)

Run:  python report.py
"""
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
import journal

load_dotenv()
client = TradingClient(os.getenv("APCA_API_KEY_ID"),
                       os.getenv("APCA_API_SECRET_KEY"), paper=True)


def build_report() -> str:
    acct = client.get_account()
    equity = float(acct.portfolio_value)
    prev = float(acct.last_equity)          # yesterday's close equity
    day_pl = equity - prev
    today = datetime.now().strftime("%Y-%m-%d")

    trades = [t for t in journal.load_trades() if t.get("ts", "").startswith(today)]
    buys = [t for t in trades if t["action"] == "BUY"]
    sells = [t for t in trades if t["action"] == "SELL"]
    closed = [t for t in sells if t.get("pnl") is not None]
    realized = sum(t["pnl"] for t in closed)
    wins = [t for t in closed if t["pnl"] > 0]
    win_rate = (len(wins) / len(closed) * 100) if closed else 0.0

    lines = []
    lines.append("=" * 56)
    lines.append(f"   PROJECT 10X  --  EARNINGS REPORT  {today}")
    lines.append("=" * 56)
    lines.append(f"  Equity now:       ${equity:,.2f}")
    lines.append(f"  Day P&L:          ${day_pl:+,.2f}  ({day_pl/prev*100:+.2f}%)")
    lines.append(f"  Progress to $1M:  {equity/1_000_000*100:.1f}%")
    lines.append("")
    lines.append(f"  Trades today:     {len(trades)}  ({len(buys)} buys, {len(sells)} sells)")
    lines.append(f"  Closed for P&L:   {len(closed)}   |  Win rate: {win_rate:.0f}%")
    lines.append(f"  Realized today:   ${realized:+,.2f}")

    if closed:
        best = max(closed, key=lambda t: t["pnl"])
        worst = min(closed, key=lambda t: t["pnl"])
        lines.append(f"  Best trade:       {best['symbol']} ${best['pnl']:+,.0f}")
        lines.append(f"  Worst trade:      {worst['symbol']} ${worst['pnl']:+,.0f}")

    lessons = journal.lessons()
    by_sym = lessons.get("by_symbol", {})
    if by_sym:
        lines.append("")
        lines.append("  What the bot has learned (lifetime avg P&L per trade):")
        for sym, s in sorted(by_sym.items(), key=lambda kv: kv[1]["avg_pnl"], reverse=True):
            lines.append(f"    {sym:<6} {s['trades']:>4} trades   avg ${s['avg_pnl']:+,.1f}")
    lines.append("=" * 56)
    return "\n".join(lines)


def maybe_email(body: str):
    addr = os.getenv("GMAIL_ADDRESS")
    pw = os.getenv("GMAIL_APP_PASSWORD")
    to = os.getenv("REPORT_TO", addr)
    if not addr or not pw:
        print("\n(Email off -- add GMAIL_ADDRESS + GMAIL_APP_PASSWORD to .env to turn it on.)")
        return
    try:
        msg = MIMEText(body)
        msg["Subject"] = f"Project 10X earnings -- {datetime.now():%Y-%m-%d}"
        msg["From"], msg["To"] = addr, to
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(addr, pw)
            s.send_message(msg)
        print(f"\n(Emailed report to {to}.)")
    except Exception as e:
        print("\n(Email failed:", type(e).__name__, e, ")")


def generate():
    body = build_report()
    print("\n" + body)
    os.makedirs("reports", exist_ok=True)
    path = os.path.join("reports", f"{datetime.now():%Y-%m-%d}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"\nSaved to {path}")
    maybe_email(body)


if __name__ == "__main__":
    generate()
