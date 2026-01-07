#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import httpx
import pandas as pd
from datetime import datetime, timedelta
from datetime import timezone

API_KEY_PATH = os.path.expanduser(
    "~/documents/python_for_finance/api_token.txt"
)

UNIVERSE_PATH = os.path.expanduser(
    "~/documents/python_for_finance/universes/nasdaq100.txt"
)

OUT_PATH = os.path.expanduser(
    "~/documents/python_for_finance/Markov/trader/intraday_trader/earnings_calendar_raw.json"
)

BASE_URL = "https://eodhistoricaldata.com/api"


# ─────────────────────────────────────────────────────────────
def load_api_key(path):
    try:
        return open(path).read().strip()
    except FileNotFoundError:
        raise SystemExit(f"❌ API-Key nicht gefunden: {path}")


def load_universe(path):
    if not os.path.exists(path):
        raise SystemExit(f"❌ NASDAQ100-Universe nicht gefunden: {path}")
    txt = open(path).read().replace("\n", ",")
    return [t.strip().upper() for t in txt.split(",") if t.strip()]


# ─────────────────────────────────────────────────────────────
def fetch_daily_earnings(client, api_key, from_date, to_date):
    """
    Holt den offiziellen täglichen Earnings-Kalender von EOD.
    """
    url = f"{BASE_URL}/calendar/earnings"
    r = client.get(url, params={
        "from": from_date,
        "to": to_date,
        "api_token": api_key,
        "fmt": "json"
    })

    if r.status_code != 200:
        raise RuntimeError("❌ Earnings-Kalender konnte nicht geladen werden")

    return r.json()


# ─────────────────────────────────────────────────────────────
def main():
    print("📡 Lade DAILY EARNINGS KALENDER…")

    api_key  = load_api_key(API_KEY_PATH)
    universe = set(load_universe(UNIVERSE_PATH))

    today = datetime.now(timezone.utc).date()
    end   = today + timedelta(days=60)

    limits  = httpx.Limits(max_connections=6)
    timeout = httpx.Timeout(10.0)

    with httpx.Client(limits=limits, timeout=timeout) as client:
        raw = fetch_daily_earnings(
            client,
            api_key,
            today.isoformat(),
            end.isoformat()
        )

    # ── DEBUG: Top-Level-Struktur ─────────────────────────────
    print("🔎 Raw Top-Level Keys:", list(raw.keys()))

    # ── DEIN ECHTES FORMAT: raw["earnings"] ist eine LISTE ────
    earnings_list = raw.get("earnings", [])

    if not isinstance(earnings_list, list):
        print("⚠️ Unerwartete Struktur für raw['earnings'] – kompletter Dump:")
        print(json.dumps(raw, indent=2))
        print("❌ Abbruch ohne Kalender-Erstellung")
        return

    print(f"✅ Anzahl Roh-Earnings weltweit: {len(earnings_list)}")

    calendar = {}

    for ev in earnings_list:

        if not isinstance(ev, dict):
            continue

        sym = ev.get("code")
        date_str = ev.get("report_date")

        if not sym or not date_str:
            continue

        # ✅ Symbol normalisieren
        sym = sym.upper().replace(".US", "").strip()

        # ✅ NUR NASDAQ100
        if sym not in universe:
            continue

        calendar.setdefault(date_str, [])
        calendar[date_str].append(sym)

    calendar_sorted = dict(sorted(calendar.items()))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(calendar_sorted, f, indent=2)

    print(f"\n💾 DAILY Earnings-Kalender gespeichert → {OUT_PATH}")
    print(f"📅 Anzahl Tage mit Events: {len(calendar_sorted)}")
    print("🔍 Vorschau:")
    for d, syms in list(calendar_sorted.items())[:5]:
        print(f"  {d}: {syms}")


if __name__ == "__main__":
    main()

