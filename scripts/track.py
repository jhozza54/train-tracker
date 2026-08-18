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
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_BASE = "https://data.rtt.io"
LONDON = ZoneInfo("Europe/London")
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


def local_hhmm(value: str | None) -> str | None:
    """RTT returns ISO 8601 that may be UTC or offset-bearing; we want UK local."""
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(LONDON)
    return parsed.strftime("%H:%M")


def resolve_token(token: str) -> str:
    """Return a token usable as a Bearer against the data endpoints.

    RTT issues either a long-life access token or a long-life *refresh* token.
    A refresh token is rejected (401) by the data endpoints and has to be
    swapped for a short-life access token first, so probe /api/info and fall
    back to the swap when the raw token isn't accepted directly.
    """
    probe = requests.get(
        f"{API_BASE}/api/info",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if probe.ok:
        return token
    if probe.status_code != 401:
        probe.raise_for_status()

    swap = requests.get(
        f"{API_BASE}/api/get_access_token",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if swap.ok:
        access = swap.json().get("token")
        if access:
            return access
        print("get_access_token returned no token field", file=sys.stderr)
        sys.exit(1)

    print(
        "RTT rejected RTT_API_TOKEN: /api/info returned 401 and the refresh-token "
        f"swap at /api/get_access_token returned {swap.status_code}. The token is "
        "most likely invalid, expired, or copied with stray whitespace.",
        file=sys.stderr,
    )
    sys.exit(1)


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
    if not resp.ok:
        print(
            f"{leg['label']}: {resp.status_code} from {resp.url} -> {resp.text[:300]}",
            file=sys.stderr,
        )
        resp.raise_for_status()
    data = resp.json()

    dep = None
    for svc in data.get("services", []):
        candidate = svc.get("temporalData", {}).get("departure")
        if not candidate:
            continue
        if local_hhmm(candidate.get("scheduleAdvertised")) == leg["scheduled"]:
            dep = candidate
            break

    if dep is None:
        # The scheduled service wasn't in the line-up at all: either it didn't run
        # or the window missed it. Either way we have no reading for the day.
        record["no_data"] = True
        return record

    record["cancelled"] = bool(dep.get("isCancelled"))
    record["lateness_minutes"] = dep.get("realtimeAdvertisedLateness")
    record["actual"] = local_hhmm(dep.get("realtimeActual"))

    return record


def main():
    token = os.environ.get("RTT_API_TOKEN")
    if not token:
        print("RTT_API_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    token = resolve_token(token.strip())

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
