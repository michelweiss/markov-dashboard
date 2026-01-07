#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download upcoming football fixtures from football-data.org
----------------------------------------------------------
• Competitions: EPL, LaLiga (extensible)
• Status: SCHEDULED, TIMED
• Output: data/<league>/upcoming_fixtures.csv
"""

import requests
import pandas as pd
from pathlib import Path
import sys

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

BASE_URL = "https://api.football-data.org/v4"

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"

TOKEN_PATH = Path.home() / "documents/python_for_finance/football_data.txt"

LEAGUES = {
    "epl": {
        "competition": "PL",
        "label": "Premier League",
    },
    "laliga": {
        "competition": "PD",
        "label": "LaLiga",
    },
    "seriea": {
        "competition": "SA",
        "label": "Serie A",
    },
    "ligue1": {
        "competition": "FL1",
        "label": "Ligue 1",
    },
    
}

# ─────────────────────────────────────────────
# TOKEN
# ─────────────────────────────────────────────

def load_token():
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(f"API token not found: {TOKEN_PATH}")
    return TOKEN_PATH.read_text().strip()


HEADERS = {
    "X-Auth-Token": load_token()
}

# ─────────────────────────────────────────────
# FETCH
# ─────────────────────────────────────────────

def fetch_fixtures(competition_code: str) -> list[dict]:
    url = f"{BASE_URL}/competitions/{competition_code}/matches"
    params = {"status": "SCHEDULED,TIMED"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("matches", [])

# ─────────────────────────────────────────────
# NORMALIZE
# ─────────────────────────────────────────────

def normalize_fixtures(matches: list[dict]) -> pd.DataFrame:
    rows = []

    for m in matches:
        rows.append({
            "utc_date": m["utcDate"],
            "matchday": m.get("matchday"),
            "home_team": m["homeTeam"]["name"],
            "away_team": m["awayTeam"]["name"],
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df.utc_date).dt.date
    return df.sort_values("date").reset_index(drop=True)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def fetch_league(league_key: str, cfg: dict):
    print(f"\n📅 Fetching fixtures: {cfg['label']}")

    matches = fetch_fixtures(cfg["competition"])
    print(f"✔ Fixtures received: {len(matches)}")

    df = normalize_fixtures(matches)
    print(f"✔ Upcoming fixtures: {len(df)}")

    out_dir = DATA_ROOT / league_key
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "upcoming_fixtures.csv"

    df.to_csv(out_file, index=False)
    print(f"💾 Saved to: {out_file}")

    if not df.empty:
        print(f"📊 Date range: {df.date.min()} → {df.date.max()}")

def main():

    # optional CLI arg: python fetch_upcoming_fixtures.py laliga
    if len(sys.argv) > 1:
        leagues = [sys.argv[1]]
    else:
        leagues = LEAGUES.keys()

    for lg in leagues:
        if lg not in LEAGUES:
            print(f"❌ Unknown league: {lg}")
            continue
        fetch_league(lg, LEAGUES[lg])

    print("\n🏁 Done.")

if __name__ == "__main__":
    main()

