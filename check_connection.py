"""
Connection test: confirms we can reach your Alpaca PAPER account.
Reads keys from .env. Does NOT place any trades — read-only.
"""
import os
import sys
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

key = os.getenv("APCA_API_KEY_ID", "")
secret = os.getenv("APCA_API_SECRET_KEY", "")

if not key or key.startswith("PASTE_") or not secret or secret.startswith("PASTE_"):
    print("ERROR: Keys not filled in yet. Open .env and paste your PAPER keys, then save.")
    sys.exit(1)

# paper=True is the safety switch: this points at the fake-money endpoint.
client = TradingClient(key, secret, paper=True)

acct = client.get_account()

print("Connected to Alpaca PAPER account.")
print(f"  Status:          {acct.status}")
print(f"  Account number:  {acct.account_number}")
print(f"  Cash:            ${float(acct.cash):,.2f}")
print(f"  Buying power:    ${float(acct.buying_power):,.2f}")
print(f"  Portfolio value: ${float(acct.portfolio_value):,.2f}")
print()
print("Read-only check complete. No trades were placed.")
