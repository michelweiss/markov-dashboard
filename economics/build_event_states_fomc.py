#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build FOMC Markov states (3-class)
---------------------------------
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "macro_actuals.csv"
OUT_FILE = DATA_DIR / "event_states_fomc.csv"


def classify_move(x):
    if x <= -0.25:
        return "CUT_25"
    elif x >= 0.25:
        return "HIKE_25"
    elif abs(x) < 0.10:
        return "HOLD"
    else:
        return "OTHER"


def build_fomc_states():

    df = pd.read_csv(IN_FILE, parse_dates=["date"])
    df = df[df.event == "FOMC"].sort_values("date").reset_index(drop=True)

    if df.empty:
        print("⚠️ No FOMC data found")
        return

    df["move"] = df["surprise"].apply(classify_move)
    df = df[df.move != "OTHER"].reset_index(drop=True)

    # Markov state: last 2 decisions
    df["prev_move"]  = df["move"].shift(1)
    df["prev2_move"] = df["move"].shift(2)

    df = df.dropna().reset_index(drop=True)

    df["state"] = list(zip(df.prev_move, df.prev2_move))
    df["outcome"] = df["move"]

    df[["date", "state", "outcome"]].to_csv(OUT_FILE, index=False)

    print(f"✔ FOMC states written: {OUT_FILE}")
    print(df.tail())


if __name__ == "__main__":
    build_fomc_states()

