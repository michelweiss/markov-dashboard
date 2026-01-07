#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate football fixture previews using p_win (State v1)
---------------------------------------------------------
• State = (Form, Home)
• Uses last N finished matches per team
• Output: data/<league>/fixture_previews.json
"""

import pandas as pd
import json
from pathlib import Path
import sys

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"

LOOKBACK = 3

LEAGUES = {
    "epl": {
        "label": "Premier League",
    },
    "laliga": {
        "label": "LaLiga",
    },
    "seriea": {
        "label": "Serie A",
    },
    "ligue1": {
        "label": "Ligue 1",
    },
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def compute_form(last_wins: list[int]) -> int | None:
    """
    Simple binary form:
    1 = >=2 wins in last LOOKBACK matches
    0 = otherwise
    """
    if len(last_wins) < LOOKBACK:
        return None
    return int(sum(last_wins[-LOOKBACK:]) >= 2)


def load_pwin_map(data_dir: Path) -> dict:
    """
    Load LEAGUE-LOCAL pwin_states.csv
    """
    file = data_dir / "pwin_states.csv"
    if not file.exists():
        raise FileNotFoundError(f"Missing pwin_states.csv: {file}")

    df = pd.read_csv(file)
    return df.set_index("state")[["p_win", "p_draw", "samples"]].to_dict("index")


# ─────────────────────────────────────────────
# CORE
# ─────────────────────────────────────────────

def generate_previews(league_key: str):

    data_dir = DATA_ROOT / league_key
    matches_file = data_dir / "team_matches.csv"
    out_file = data_dir / "fixture_previews.json"

    print(f"\n🔮 Generating previews: {league_key.upper()}")

    if not matches_file.exists():
        print(f"⚠️ Missing team_matches.csv for {league_key}")
        return

    df = pd.read_csv(matches_file, parse_dates=["date"])
    df = df.sort_values(["team", "date"])

    last_date = df.date.max()

    # ✅ LEAGUE-LOCAL pwin map
    pwin_map = load_pwin_map(data_dir)
    previews = []

    for team, g in df.groupby("team"):
        g = g[g.date <= last_date]

        last_wins = g.win.tolist()[-LOOKBACK:]
        form = compute_form(last_wins)

        if form is None:
            continue

        for is_home in (1, 0):
            state = f"({form},{is_home})"
            state_probs = pwin_map.get(state)

            if state_probs is None:
                continue

            previews.append({
                "team": team,
                "form": form,
                "is_home": is_home,
                "state": state,
                "p_win": round(float(state_probs["p_win"]), 3),
                "p_draw": round(float(state_probs["p_draw"]), 3),
                "samples": int(state_probs["samples"]),
                "as_of": str(last_date.date()),
            })

    if not previews:
        print("⚠️ No previews generated.")
        return

    out_file.write_text(json.dumps(previews, indent=2))
    print(f"✔ fixture_previews.json written ({len(previews)} rows)")
    print(f"📁 {out_file}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():

    # optional CLI arg: python3 generate_fixture_previews.py seriea
    if len(sys.argv) > 1:
        leagues = [sys.argv[1]]
    else:
        leagues = LEAGUES.keys()

    for lg in leagues:
        if lg not in LEAGUES:
            print(f"❌ Unknown league: {lg}")
            continue
        generate_previews(lg)

    print("\n🏁 Done.")


if __name__ == "__main__":
    main()

