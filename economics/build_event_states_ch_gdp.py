#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build event_states_ch_gdp.csv
----------------------------
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "macro_actuals.csv"
OUT_FILE = DATA_DIR / "event_states_ch_gdp.csv"


def gdp_bin_ch(x):
    if x >= 1.0:
        return "EXPANSION"
    elif x >= 0.3:
        return "MODERATE"
    elif x >= -0.3:
        return "STALL"
    else:
        return "CONTRACTION"


def build_states():

    df = pd.read_csv(IN_FILE, parse_dates=["date"])
    df = df[df.event == "CH GDP"].sort_values("date").reset_index(drop=True)

    df["trend_up"] = (
        df["actual"]
        .rolling(4)
        .mean()
        .diff()
        .gt(0)
        .astype(int)
    )

    df["last_bin"] = df["actual"].shift(1).apply(gdp_bin_ch)
    df = df.dropna().reset_index(drop=True)

    df["state"] = list(zip(df.trend_up, df.last_bin))
    df["outcome"] = df["actual"].apply(gdp_bin_ch)

    df.to_csv(OUT_FILE, index=False)
    print(f"✔ EU GDP states written: {OUT_FILE}")


if __name__ == "__main__":
    build_states()

