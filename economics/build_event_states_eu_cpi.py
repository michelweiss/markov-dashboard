#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build event_states_eu_cpi.csv
-----------------------------
EU CPI: Above / Below
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "macro_actuals.csv"
OUT_FILE = DATA_DIR / "event_states_eu_cpi.csv"


def build_states():

    df = pd.read_csv(IN_FILE, parse_dates=["date"])
    df = df[df.event == "EU CPI"].sort_values("date").reset_index(drop=True)

    # 6M trend
    df["trend_up"] = (
        df["actual"]
        .rolling(6)
        .mean()
        .diff()
        .gt(0)
        .astype(int)
    )

    df["last_surprise_pos"] = df["surprise"].shift(1).gt(0).astype(int)

    df = df.dropna().reset_index(drop=True)

    df["state"] = list(zip(df.trend_up, df.last_surprise_pos))
    df["outcome"] = df["surprise"].gt(0).map({True: "ABOVE", False: "BELOW"})

    df.to_csv(OUT_FILE, index=False)
    print(f"✔ EU CPI states written: {OUT_FILE}")


if __name__ == "__main__":
    build_states()

