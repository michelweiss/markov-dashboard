#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "snb_policy_rate.csv"
OUT_FILE = DATA_DIR / "event_states_snb.csv"


def build_states():

    df = pd.read_csv(IN_FILE, parse_dates=["date"])
    df = df.sort_values("date")

    df["delta"] = df["rate"].diff()

    def outcome(x):
        if x > 0:
            return "HIKE"
        elif x < 0:
            return "CUT"
        else:
            return "HOLD"

    df["outcome"] = df["delta"].apply(outcome)

    # Markov state = last 2 outcomes
    df["state"] = (
        df["outcome"].shift(2).fillna("HOLD") + "_" +
        df["outcome"].shift(1).fillna("HOLD")
    )

    out = df.dropna(subset=["state", "outcome"])[
        ["date", "state", "outcome"]
    ]

    out.to_csv(OUT_FILE, index=False)
    print(f"✔ SNB event states written: {OUT_FILE}")
    print(out.tail())


if __name__ == "__main__":
    build_states()

