#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build GDP Markov states with bins
--------------------------------
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "macro_actuals.csv"
OUT_FILE = DATA_DIR / "event_states_gdp.csv"


def gdp_bin(x):
    if x >= 3.0:
        return "EXPANSION"
    elif x >= 1.5:
        return "MODERATE"
    elif x >= 0.0:
        return "STALL"
    else:
        return "CONTRACTION"


def build_gdp_states():

    df = pd.read_csv(IN_FILE, parse_dates=["date"])
    df = df[df.event == "US GDP"].sort_values("date").reset_index(drop=True)

    if df.empty:
        print("⚠️ No GDP data found")
        return

    df["bin"] = df["actual"].apply(gdp_bin)

    # Markov state: last 2 bins
    df["prev_bin"]  = df["bin"].shift(1)
    df["prev2_bin"] = df["bin"].shift(2)

    df = df.dropna().reset_index(drop=True)

    df["state"] = list(zip(df.prev_bin, df.prev2_bin))
    df["outcome"] = df["bin"]

    df[["date", "state", "outcome"]].to_csv(OUT_FILE, index=False)

    print(f"✔ GDP states written: {OUT_FILE}")
    print(df.tail())


if __name__ == "__main__":
    build_gdp_states()

