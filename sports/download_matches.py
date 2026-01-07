#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download football match history from football-data.org
------------------------------------------------------
• Competitions: EPL, LaLiga (extensible)
• Time range: ALL available seasons
• Output: data/<league>/raw_matches.csv
"""

import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

BASE_URL = "https://api.football-data.org/v4"

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"

TOKEN_PATH = Path.home() / "documents/python_for_finance/football_data.txt"

# football-data.org competition codes
LEAGUES = {
    "epl": {
        "competition": "PL",   # Premier League (England)
        "label": "Premier League",
    },
    "laliga": {
        "competition": "PD",   # Primera División (LaLiga, Spanien)
        "label": "LaLiga",
    },
    "seriea": {
        "competition": "SA",   # Serie A (Italien)
        "label": "Serie A",
    },
    "ligue1": {
        "competition": "FL1",   # Ligue 1 (Frankreich)
        "label": "Ligue 1",
    },
    
}

# ─────────────────────────────────────────────
# TOKEN
# ─────────────────────────────────────────────

def load_token() -> str:
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(f"API token not found: {TOKEN_PATH}")
    return TOKEN_PATH.read_text().strip()


HEADERS = {
    "X-Auth-Token": load_token()
}

# ─────────────────────────────────────────────
# FETCH MATCHES
# ─────────────────────────────────────────────

def fetch_all_matches(competition_code: str) -> list[dict]:
    """
    Fetch all available matches for a competition.
    """
    url = f"{BASE_URL}/competitions/{competition_code}/matches"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("matches", [])

# ─────────────────────────────────────────────
# NORMALIZE
# ─────────────────────────────────────────────

def normalize_matches(matches: list[dict]) -> pd.DataFrame:
    rows = []

    for m in matches:
        score = m.get("score", {}).get("fullTime", {})
        home_goals = score.get("home")
        away_goals = score.get("away")

        # only finished matches
        if home_goals is None or away_goals is None:
            continue

        rows.append({
            "date": pd.to_datetime(m["utcDate"]).date(),
            "season": m["season"]["startDate"][:4],
            "home_team": m["homeTeam"]["name"],
            "away_team": m["awayTeam"]["name"],
            "home_goals": int(home_goals),
            "away_goals": int(away_goals),
            "home_win": int(home_goals > away_goals),
            "away_win": int(away_goals > home_goals),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("date").reset_index(drop=True)
    return df

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def fetch_league(league_key: str, cfg: dict):
    print(f"\n⚽ Downloading {cfg['label']} history …")

    matches = fetch_all_matches(cfg["competition"])
    print(f"✔ Matches received: {len(matches)}")

    df = normalize_matches(matches)
    print(f"✔ Finished matches: {len(df)}")

    out_dir = DATA_ROOT / league_key
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "raw_matches.csv"

    df.to_csv(out_file, index=False)
    print(f"💾 Saved to: {out_file}")

    if not df.empty:
        print(f"📊 Date range: {df.date.min()} → {df.date.max()}")


def main():

    # optional CLI arg: python fetch_matches_football_data.py laliga
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

