"""
Team 10X idea emailer. Sends Race one market-research idea per run.
Scheduled 3x/day by GitHub Actions (8am / noon / 3pm ET). Uses only stdlib.

Reads ideas from ideas.json, picks one based on the date+time so the three
daily emails differ, and sends it via Gmail SMTP using repo secrets:
  GMAIL_ADDRESS, GMAIL_APP_PASSWORD, REPORT_TO
"""
import os
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

with open("ideas.json", encoding="utf-8") as f:
    ideas = json.load(f)

now = datetime.now()
idx = (now.timetuple().tm_yday * 3 + now.hour) % len(ideas)
idea = ideas[idx]

addr = os.getenv("GMAIL_ADDRESS")
pw = os.getenv("GMAIL_APP_PASSWORD")
to = os.getenv("REPORT_TO", addr)

if not (addr and pw and to):
    print("Email secrets missing -- skipping (set GMAIL_ADDRESS / GMAIL_APP_PASSWORD / REPORT_TO).")
    raise SystemExit(0)

body = (
    f"Yo Race,\n\n"
    f"Idea for the bot:\n\n{idea}\n\n"
    f"Reply 'yes' next time we talk and I'll wire it into the research brain. "
    f"Even a 'nah' is useful data.\n\n"
    f"- Claude (Team 10X)"
)
msg = MIMEText(body)
msg["Subject"] = f"Team 10X idea - {now:%b %d, %I%p}"
msg["From"] = addr
msg["To"] = to

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(addr, pw)
    s.send_message(msg)

print(f"Sent idea to {to}: {idea[:60]}...")
