#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import httpx
import pandas as pd
from datetime import datetime

API_KEY_PATH = os.path.expanduser("~/documents/python_for_finance/api_token.txt")

# NASDAQ100 Universum
UNIVERSE_PATH = os.path.expanduser(
    "~/documents/python_for_finance/universes/nasdaq100.txt"
)

OUT_PATH = os.path.expanduser(
    "~/documents/python_for_finance/Markov/trader/intraday_trader/earnings_calendar_raw.json"
)

BASE_URL = "https://eodhistoricaldata.com/api"


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


def fetch_earnings_for_symbol(client, symbol, api_key):
    """
    Holt Earnings Events für ein Symbol.
    Neu: NUR für das aktuelle Jahr (z. B. 2025).
    """

    THIS_YEAR = datetime.now().year
    START = pd.to_datetime(f"{THIS_YEAR}-01-01").date()
    END   = pd.to_datetime(f"{THIS_YEAR}-12-31").date()

    url = f"{BASE_URL}/fundamentals/{symbol}"

    try:
        r = client.get(url, params={"api_token": api_key, "fmt": "json"})
        if r.status_code != 200:
            return None

        data = r.json()
        earnings = data.get("Earnings", {})
        hist = earnings.get("History") or earnings.get("history")

        if not hist:
            return None

        events = []
        for dt, row in hist.items():
            try:
                date_obj = pd.to_datetime(dt).date()
            except Exception:
                continue

            # 🔥 Filter: nur aktuelles Jahr
            if not (START <= date_obj <= END):
                continue

            events.append({
                "symbol": symbol,
                "earnings_date": date_obj.isoformat(),
                "eps": row.get("eps"),
                "revenue": row.get("revenue"),
                "period": row.get("period")
            })

        return events if events else None

    except Exception:
        return None


def main():
    print("📡 Lade EOD Earnings für NASDAQ100…")

    api_key = load_api_key(API_KEY_PATH)
    universe = load_universe(UNIVERSE_PATH)

    calendar = {}

    limits = httpx.Limits(max_connections=6)
    timeout = httpx.Timeout(10.0)

    with httpx.Client(limits=limits, timeout=timeout) as client:
        for i, sym in enumerate(universe, 1):
            print(f"[{i}/{len(universe)}] → {sym}")

            events = fetch_earnings_for_symbol(client, sym, api_key)
            if not events:
                continue

            for e in events:
                d = e["earnings_date"]
                calendar.setdefault(d, [])
                calendar[d].append(e["symbol"])

    # Sortieren
    calendar_sorted = dict(sorted(calendar.items()))

    # Speichern
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(calendar_sorted, f, indent=2)

    print(f"\n💾 Earnings-Kalender gespeichert → {OUT_PATH}")
    print(f"📅 Anzahl Tage mit Events: {len(calendar_sorted)}")
    print("🔍 Beispiel:")
    sample = list(calendar_sorted.items())[:5]
    for d, syms in sample:
        print(f"  {d}: {syms}")


if __name__ == "__main__":
    main()

