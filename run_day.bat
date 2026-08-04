@echo off
cd /d C:\Users\racei\alpaca-bot
if not exist logs mkdir logs
.venv\Scripts\python.exe run_day.py --live >> logs\autopilot.log 2>&1
