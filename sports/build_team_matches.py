#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build team-level match table from raw_matches.csv
-------------------------------------------------
• Input : data/<league>/raw_matches.csv
• Output: data/<league>/team_matches.csv
"""

import pandas as pd
from pathlib import Path
import sys

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"

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
    "ligue1": {
        "sport": "soccer_france_ligue_one",
        "label": "Ligue 1",
    },
}

# ─────────────────────────────────────────────
# CORE
# ─────────────────────────────────────────────

def build_team_table(league_key: str):

    data_dir = DATA_ROOT / league_key
    in_file  = data_dir / "raw_matches.csv"
    out_file = data_dir / "team_matches.csv"

    print(f"\n🧱 Building team_matches: {league_key.upper()}")

    if not in_file.exists():
        print(f"⚠️ Missing raw_matches.csv for {league_key}")
        return

    df = pd.read_csv(in_file, parse_dates=["date"])

    rows = []

    for _, r in df.iterrows():
        # home team
        rows.append({
            "date": r.date,
            "season": r.season,
            "team": r.home_team,
            "opponent": r.away_team,
            "is_home": 1,
            "win": int(r.home_goals > r.away_goals),
            "draw": int(r.home_goals == r.away_goals),
        })

        # away team
        rows.append({
            "date": r.date,
            "season": r.season,
            "team": r.away_team,
            "opponent": r.home_team,
            "is_home": 0,
            "win": int(r.away_goals > r.home_goals),
            "draw": int(r.home_goals == r.away_goals),
        })

    out = (
        pd.DataFrame(rows)
        .sort_values(["team", "date"])
        .reset_index(drop=True)
    )

    out.to_csv(out_file, index=False)
    print(f"✔ team_matches.csv written ({len(out)} rows)")
    print(f"📁 {out_file}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():

    # optional CLI arg: python build_team_matches.py laliga
    if len(sys.argv) > 1:
        leagues = [sys.argv[1]]
    else:
        leagues = LEAGUES.keys()

    for lg in leagues:
        if lg not in LEAGUES:
            print(f"❌ Unknown league: {lg}")
            continue
        build_team_table(lg)

    print("\n🏁 Done.")


if __name__ == "__main__":
    main()

