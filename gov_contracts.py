"""
GOV CONTRACTS research input -- real, free, public data from USASpending.gov.
When a public company lands a big federal contract, that's a real, tradable
catalyst. No API key needed. Pulls the largest recent contract awards.

Run:  python gov_contracts.py
"""
import json
import urllib.request
from datetime import datetime, timedelta

API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


def recent_contracts(limit=15, days=120):
    end = datetime.now().date()
    start = end - timedelta(days=days)
    payload = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],
            "time_period": [{"start_date": str(start), "end_date": str(end)}],
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount",
                   "Awarding Agency", "Description"],
        "sort": "Award Amount",
        "order": "desc",
        "limit": limit,
    }
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("results", [])


if __name__ == "__main__":
    print("Largest recent federal contract awards (USASpending.gov):\n")
    try:
        for c in recent_contracts():
            amt = c.get("Award Amount") or 0
            name = (c.get("Recipient Name") or "?")[:38]
            agency = (c.get("Awarding Agency") or "")[:22]
            print(f"  ${amt:>15,.0f}  {name:<38}  {agency}")
    except Exception as e:
        print("ERROR:", type(e).__name__, e)
        print("(Needs internet access; will run fine in the cloud/Actions runner.)")
