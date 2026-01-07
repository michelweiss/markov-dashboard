#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "event_states_snb.csv"
OUT_FILE = DATA_DIR / "pwin_snb.csv"

SHRINK_K = 10


def shrink(p, n, k=SHRINK_K):
    return (p * n + (1/3) * k) / (n + k)


def build_pwin():

    df = pd.read_csv(IN_FILE)
    rows = []

    for state, g in df.groupby("state"):
        n = len(g)

        for outcome in ["CUT", "HOLD", "HIKE"]:
            wins = (g["outcome"] == outcome).sum()
            p_raw = wins / n if n > 0 else 1/3
            p = shrink(p_raw, n)

            rows.append({
                "state": state,
                "outcome": outcome,
                "samples": n,
                "wins": wins,
                "p_raw": round(p_raw, 3),
                "p_shrunk": round(p, 3),
            })

    out = (
        pd.DataFrame(rows)
        .sort_values(["state", "p_shrunk"], ascending=False)
    )

    out.to_csv(OUT_FILE, index=False)
    print(f"✔ SNB pwin written: {OUT_FILE}")
    print(out)


if __name__ == "__main__":
    build_pwin()

