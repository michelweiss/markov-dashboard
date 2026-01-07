#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build CPI event states (3-class)
--------------------------------
Outcome: below / inline / above
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "macro_actuals.csv"
OUT_FILE = DATA_DIR / "event_states_cpi.csv"


def classify_cpi(s):
    if s <= -0.1:
        return "below"
    elif s >= 0.1:
        return "above"
    else:
        return "inline"


def build_states():

    df = pd.read_csv(IN_FILE, parse_dates=["date"])
    df = df[df.event == "US CPI"].sort_values("date").reset_index(drop=True)

    # 6M trend
    df["trend_up"] = (
        df["actual"]
        .rolling(6)
        .mean()
        .diff()
        .gt(0)
        .astype(int)
    )

    df["last_outcome"] = df["surprise"].shift(1).apply(classify_cpi)

    df = df.dropna().reset_index(drop=True)

    df["state"] = list(zip(df.trend_up, df.last_outcome))
    df["outcome"] = df["surprise"].apply(classify_cpi)

    df.to_csv(OUT_FILE, index=False)

    print(f"✔ CPI states written: {OUT_FILE}")
    print(df.tail())


if __name__ == "__main__":
    build_states()

