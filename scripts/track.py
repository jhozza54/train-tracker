#!/usr/bin/env python3
"""
Fetches actual departure data for James's three commuter train legs from the
Realtime Trains (RTT) Next Generation API and appends the results to
data/history.json.

Requires the RTT_API_TOKEN environment variable — a Bearer token from
https://api-portal.rtt.io/

Run manually with:  RTT_API_TOKEN=xxxx python scripts/track.py
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

import requests

API_BASE = "https://data.rtt.io"
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "history.json"

# James's three commuter legs. Times are local (Europe/London) scheduled
# departure times from the origin station. search_from/search_to define a
# window (local time — RTT assumes the local timezone of the station when
# no offset is given) wide enough to still catch the right service if it's
# running late.
LEGS = [
    {
        "id": "wnm_bth",
        "label": "Weston Milton -> Bath Spa",
        "origin": "WNM",
        "destination": "BTH",
        "scheduled": "07:57",
        "search_from": "07:40",
        "search_to": "08:40",
    },
    {
        "id": "bth_bri",
        "label": "Bath Spa -> Bristol Temple Meads",
        "origin": "BTH",
        "destination": "BRI",
        "scheduled": "17:22",
        "search_from": "17:05",
        "search_to": "17:50",
    },
    {
        "id": "bri_wnm",
        "label": "Bristol Temple Meads -> Weston Milton",
        "origin": "BRI",
        "destination": "WNM",
        "scheduled": "17:52",
        "search_from": "17:40",
        "search_to": "18:40",
    },
]


def fetch_leg(leg: dict, day: str, token: str) -> dict:
    url = f"{API_BASE}/rtt/location"
    params = {
        "code": f"gb-nr:{leg['origin']}",
        "filterTo": f"gb-nr:{leg['destination']}",
        "timeFrom": f"{day}T{leg['search_from']}:00",
        "timeTo": f"{day}T{leg['search_to']}:00",
    }
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, params=params, headers=headers, timeout=20)

    record = {
        "date": day,
        "leg": leg["id"],
        "scheduled": leg["scheduled"],
        "actual": None,
        "lateness_minutes": None,
        "cancelled": False,
        "no_data": False,
    }

    if resp.status_code == 204:
        record["no_data"] = True
        return record
    resp.raise_for_status()
    data = resp.json()

    services = data.get("services", [])
    best = None
    for svc in services:
        dep = svc.get("temporalData", {}).get("departure")
        if dep:
            best = svc
            break

    if best is None:
        record["no_data"] = True
        return record

    dep = best["temporalData"]["departure"]
    record["cancelled"] = bool(dep.get("isCancelled"))
    record["lateness_minutes"] = dep.get("realtimeAdvertisedLateness")
    actual = dep.get("realtimeActual")
    if actual:
        record["actual"] = actual[11:16]  # HH:MM out of the ISO datetime

    return record


def main():
    token = os.environ.get("RTT_API_TOKEN")
    if not token:
        print("RTT_API_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    day = date.today().isoformat()

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        store = json.loads(DATA_FILE.read_text())
    else:
        store = {"records": []}

    existing_keys = {(r["date"], r["leg"]) for r in store["records"]}

    for leg in LEGS:
        if (day, leg["id"]) in existing_keys:
            continue  # already logged today
        record = fetch_leg(leg, day, token)
        store["records"].append(record)
        print(f"{leg['label']}: {record}")

    store["records"].sort(key=lambda r: (r["date"], r["leg"]))
    DATA_FILE.write_text(json.dumps(store, indent=2))


if __name__ == "__main__":
    main()
