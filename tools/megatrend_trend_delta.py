#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Megatrend → Trend-Delta Overlay (Monthly Momentum)
--------------------------------------------------
Variante: Letzter Monatsultimo → aktuelles Rebalancing

Berechnet pro Megatrend:
- 1M-Return der real allokierten Titel (Option A)
- Relatives Delta vs. Durchschnitt aller Trends
- Taktischen Overlay-Faktor für das Positions-Sizing
"""

import json
import os
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import httpx

# -------------------------------------------------
# Pfade
# -------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent  # → .../Markov
MEGATREND_DIR = ROOT / "trader" / "megatrend"

ALLOC_FILE = MEGATREND_DIR / "data" / "current_allocation.json"
OUT_FILE   = MEGATREND_DIR / "data" / "trend_delta_overlay.json"

API_KEY_FILE = Path.home() / "documents/python_for_finance/api_token.txt"

BASE_URL = "https://eodhistoricaldata.com/api"

# -------------------------------------------------
# Parameter
# -------------------------------------------------
DELTA_STRENGTH = 1.5      # Wie stark Trend-Deltas die Gewichte beeinflussen
MAX_BOOST = 0.30          # Maximal +30%
MAX_CUT   = -0.30         # Maximal -30%

# -------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------
def load_api_key():
    if not API_KEY_FILE.exists():
        raise RuntimeError("❌ API Key nicht gefunden")
    return API_KEY_FILE.read_text().strip()

def last_month_ultimo(date: pd.Timestamp) -> pd.Timestamp:
    first = date.replace(day=1)
    last_prev = first - pd.Timedelta(days=1)
    return last_prev

def fetch_close(ticker: str, start: str, end: str, api_key: str):
    url = f"{BASE_URL}/eod/{ticker}"
    params = {
        "api_token": api_key,
        "from": start,
        "to": end,
        "period": "d",
        "fmt": "json",
        "adjusted": "splitdiv"
    }
    r = httpx.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    if not data:
        return None

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return float(df["close"].iloc[-1])


# -------------------------------------------------
# Hauptlogik
# -------------------------------------------------
def compute_trend_delta_overlay():

    if not ALLOC_FILE.exists():
        raise FileNotFoundError("❌ current_allocation.json nicht gefunden")

    with open(ALLOC_FILE, "r", encoding="utf-8") as f:
        alloc = json.load(f)

    as_of = pd.to_datetime(alloc["as_of"])
    start_date = last_month_ultimo(as_of)

    api_key = load_api_key()

    trend_returns = {}
    trend_details = {}

    for trend, data in alloc["trends"].items():
        tickers = data.get("tickers", [])

        rets = []

        for t in tickers:
            try:
                p0 = fetch_close(
                    t,
                    start_date.strftime("%Y-%m-%d"),
                    start_date.strftime("%Y-%m-%d"),
                    api_key
                )

                p1 = fetch_close(
                    t,
                    start_date.strftime("%Y-%m-%d"),
                    as_of.strftime("%Y-%m-%d"),
                    api_key
                )

                if p0 and p1 and p0 > 0:
                    r = (p1 / p0) - 1.0
                    rets.append(r)

            except Exception as e:
                print(f"⚠️ Fehler bei {t}: {e}")

        if rets:
            trend_ret = float(pd.Series(rets).mean())
        else:
            trend_ret = 0.0

        trend_returns[trend] = trend_ret
        trend_details[trend] = {
            "tickers": tickers,
            "avg_return": round(trend_ret, 4)
        }

    # -------------------------------------------------
    # Delta vs. Durchschnitt berechnen
    # -------------------------------------------------
    avg_all = float(pd.Series(list(trend_returns.values())).mean())

    overlay = {}

    for trend, r in trend_returns.items():
        delta = r - avg_all

        delta = max(MAX_CUT, min(MAX_BOOST, delta))

        factor = 1.0 + delta * DELTA_STRENGTH

        overlay[trend] = {
            "trend_return": round(r, 4),
            "delta_vs_mean": round(delta, 4),
            "overlay_factor": round(factor, 4)
        }

    out = {
        "as_of": as_of.strftime("%Y-%m-%d"),
        "from": start_date.strftime("%Y-%m-%d"),
        "method": "Ultimo → Rebalancing (Option A: Reale Titel)",
        "overlay": overlay,
        "details": trend_details
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    return out


# -------------------------------------------------
# CLI Test
# -------------------------------------------------
if __name__ == "__main__":
    res = compute_trend_delta_overlay()

    print("✅ Trend-Delta Overlay berechnet:")
    for k, v in res["overlay"].items():
        print(f"{k:30s} → Return: {v['trend_return']:+.2%}  |  Faktor: {v['overlay_factor']:.3f}")

    print("\n📁 Output:", OUT_FILE)

