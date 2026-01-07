#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build ECB event states (3-class)
--------------------------------
State definition (minimal & robust):

state = (
    prev_decision,   # -1 = CUT | 0 = HOLD | +1 = HIKE
)

Outcome:
    CUT / HOLD / HIKE
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "ecb_decisions.csv"
OUT_FILE = DATA_DIR / "event_states_ecb.csv"


def classify_decision(x: float) -> int:
    if x > 0:
        return 1     # HIKE
    elif x < 0:
        return -1    # CUT
    else:
        return 0     # HOLD


def classify_outcome(x: float) -> str:
    if x > 0:
        return "HIKE"
    elif x < 0:
        return "CUT"
    else:
        return "HOLD"


def build_states():

    df = pd.read_csv(IN_FILE, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # classify current decision
    df["decision"] = df["actual"].apply(classify_decision)

    # previous decision → state
    df["prev_decision"] = df["decision"].shift(1)

    # drop first (no previous state)
    df = df.dropna().reset_index(drop=True)

    df["state"] = list(zip(df["prev_decision"].astype(int)))

    df["outcome"] = df["actual"].apply(classify_outcome)

    out = df[["date", "state", "outcome"]]

    out.to_csv(OUT_FILE, index=False)

    print(f"✔ ECB event states written: {OUT_FILE}")
    print(out.tail())


if __name__ == "__main__":
    build_states()

