#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import pandas as pd
from pathlib import Path
import datetime as dt
import sys
import unicodedata
import re

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"

API_KEY_FILE = Path.home() / "documents/python_for_finance/the_odds_api.txt"

BASE_URL = "https://api.the-odds-api.com/v4/sports"
REGIONS = "eu,us"
MARKETS = "h2h"
BOOKMAKER = "pinnacle"

LEAGUES = {
    "epl": {
        "sport": "soccer_epl",
        "label": "Premier League",
    },
    "laliga": {
        "sport": "soccer_spain_la_liga",
        "label": "LaLiga",
    },
    "seriea": {
        "sport": "soccer_italy_serie_a",
        "label": "Serie A",
    },
    "bundesliga": {
        "sport": "soccer_germany_bundesliga",
        "label": "Bundesliga",
    },
}


# ─────────────────────────────────────────────
# NORMALIZER (🔥 KEY FIX)
# ─────────────────────────────────────────────

def norm_team(x: str) -> str:
    if not isinstance(x, str):
        return ""

    x = unicodedata.normalize("NFKD", x)
    x = "".join(c for c in x if not unicodedata.combining(c))
    x = x.lower().strip()

    x = (
        x.replace("&", "and")
         .replace(".", " ")
         .replace("-", " ")
    )

    x = " ".join(x.split())
    return x


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def load_api_key() -> str:
    key = API_KEY_FILE.read_text().strip()
    if not key:
        raise RuntimeError("TheOddsAPI key file is empty")
    return key


def odds_to_probs(odds):
    inv = [1.0 / o for o in odds]
    s = sum(inv)
    return [x / s for x in inv]

# ─────────────────────────────────────────────
# FETCHER
# ─────────────────────────────────────────────

def fetch_league(league_key: str, cfg: dict, api_key: str):

    sport = cfg["sport"]
    out_dir = DATA_ROOT / league_key
    out_file = out_dir / "market_pinnacle.csv"

    print(f"\n⚽ Fetching Pinnacle odds: {cfg['label']}")

    url = f"{BASE_URL}/{sport}/odds"
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": "decimal",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    rows = []

    for event in data:
        home_raw = event["home_team"]
        away_raw = event["away_team"]

        home = norm_team(home_raw)
        away = norm_team(away_raw)

        books = [b for b in event.get("bookmakers", []) if b["key"] == BOOKMAKER]
        if not books:
            continue

        h2h = next((m for m in books[0]["markets"] if m["key"] == "h2h"), None)
        if not h2h:
            continue

        prices = {
            norm_team(o["name"]): o["price"]
            for o in h2h["outcomes"]
        }

        if home not in prices or away not in prices or "draw" not in prices:
            continue

        p_home, p_draw, p_away = odds_to_probs([
            prices[home],
            prices["draw"],
            prices[away],
        ])

        rows.append({
            "home_team": home,
            "away_team": away,
            "p_home_market": p_home,
            "p_draw_market": p_draw,
            "p_away_market": p_away,
            "bookmaker": "Pinnacle",
            "event_time": event["commence_time"],
            "snapshot_time": dt.datetime.now(dt.timezone.utc).isoformat(),
        })

    if not rows:
        print("⚠️ No Pinnacle odds found.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_file, index=False)

    print(f"✔ {len(rows)} matches written → {out_file}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    api_key = load_api_key()

    leagues = [sys.argv[1]] if len(sys.argv) > 1 else LEAGUES.keys()

    for lg in leagues:
        if lg not in LEAGUES:
            print(f"❌ Unknown league: {lg}")
            continue
        fetch_league(lg, LEAGUES[lg], api_key)


if __name__ == "__main__":
    main()

