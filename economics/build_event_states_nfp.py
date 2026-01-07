#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build NFP event states (3-class)
--------------------------------
Outcome: miss / inline / beat
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "macro_actuals.csv"
OUT_FILE = DATA_DIR / "event_states_nfp.csv"


def classify_nfp(s):
    if s <= -50_000:
        return "miss"
    elif s >= 50_000:
        return "beat"
    else:
        return "inline"


def build_states():

    df = pd.read_csv(IN_FILE, parse_dates=["date"])
    df = df[df.event == "US NFP"].sort_values("date").reset_index(drop=True)

    # 6M labor trend (job momentum)
    df["trend_up"] = (
        df["actual"]
        .rolling(6)
        .mean()
        .diff()
        .gt(0)
        .astype(int)
    )

    df["last_outcome"] = df["surprise"].shift(1).apply(classify_nfp)

    df = df.dropna().reset_index(drop=True)

    df["state"] = list(zip(df.trend_up, df.last_outcome))
    df["outcome"] = df["surprise"].apply(classify_nfp)

    df.to_csv(OUT_FILE, index=False)

    print(f"✔ NFP states written: {OUT_FILE}")
    print(df.tail())


if __name__ == "__main__":
    build_states()

