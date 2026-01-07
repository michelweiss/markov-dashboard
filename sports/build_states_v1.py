#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build team_states.csv from team_matches.csv (league-aware)
----------------------------------------------------------
• State = (relative_form, is_home)
• relative_form ∈ {-1, 0, +1}
• Output: data/<league>/team_states.csv
"""

import pandas as pd
from pathlib import Path
import sys

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"

LOOKBACK = 3

LEAGUES = ["epl", "laliga", "seriea", "ligue1",]   

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def compute_form(wins):
    """
    Binary form:
    1 = >=2 wins in last LOOKBACK matches
    0 = otherwise
    """
    return int(sum(wins[-LOOKBACK:]) >= 2) if len(wins) >= LOOKBACK else None


# ─────────────────────────────────────────────
# CORE
# ─────────────────────────────────────────────

def build_states(league: str):

    data_dir = DATA_ROOT / league
    in_file  = data_dir / "team_matches.csv"
    out_file = data_dir / "team_states.csv"

    print(f"\n🧠 Building team_states: {league.upper()}")

    if not in_file.exists():
        print(f"⚠️ Missing team_matches.csv for {league}")
        return

    df = pd.read_csv(in_file, parse_dates=["date"])
    df = df.sort_values(["team", "date"])

    # 1) Form pro Team berechnen
    forms = []
    for team, g in df.groupby("team"):
        wins = []
        for _, r in g.iterrows():
            f = compute_form(wins)
            wins.append(r.win)
            forms.append({
                "date": r.date,
                "team": team,
                "form": f
            })

    fdf = pd.DataFrame(forms)

    # 2) Eigene Form mergen
    df = df.merge(fdf, on=["date", "team"], how="left")

    # 3) Gegner-Form mergen (self join)
    df = df.merge(
        fdf.rename(columns={"team": "opponent", "form": "opp_form"}),
        on=["date", "opponent"],
        how="left"
    )

    rows = []
    for _, r in df.iterrows():
        if pd.isna(r.form) or pd.isna(r.opp_form):
            continue

        rel_form = int(r.form - r.opp_form)  # {-1,0,+1}
        state = f"({rel_form},{int(r.is_home)})"

        rows.append({
            "date": r.date,
            "season": r.season,
            "team": r.team,
            "opponent": r.opponent,
            "is_home": int(r.is_home),
            "form": int(r.form),
            "opp_form": int(r.opp_form),
            "rel_form": rel_form,
            "state": state,
            "win": int(r.win),
            "draw": int(r.draw),
        })

    out = pd.DataFrame(rows).sort_values(["team", "date"])
    out.to_csv(out_file, index=False)

    print(f"✔ team_states.csv written ({len(out)} rows)")
    print(out.state.value_counts())


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():

    # optional: python build_states_v1.py laliga
    if len(sys.argv) > 1:
        leagues = [sys.argv[1]]
    else:
        leagues = LEAGUES

    for lg in leagues:
        if lg not in LEAGUES:
            print(f"❌ Unknown league: {lg}")
            continue
        build_states(lg)

    print("\n🏁 Done.")


if __name__ == "__main__":
    main()



