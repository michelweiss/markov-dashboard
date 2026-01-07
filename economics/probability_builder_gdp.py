#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build GDP bin probabilities
---------------------------
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "event_states_gdp.csv"
OUT_FILE = DATA_DIR / "pwin_gdp.csv"

SHRINK_K = 15


def shrink(p, n, k=SHRINK_K):
    return (p * n + 0.25 * k) / (n + k)


def build_gdp_pwin():

    df = pd.read_csv(IN_FILE)

    rows = []

    for state, g in df.groupby("state"):
        n = len(g)

        for outcome in g.outcome.unique():
            wins = (g.outcome == outcome).sum()
            p_raw = wins / n
            p = shrink(p_raw, n)

            rows.append({
                "state": state,
                "outcome": outcome,
                "samples": n,
                "p_raw": round(p_raw, 4),
                "p_shrunk": round(p, 4),
            })

    out = pd.DataFrame(rows).sort_values(["state", "outcome"])
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ GDP probabilities written: {OUT_FILE}")
    print(out.tail())


if __name__ == "__main__":
    build_gdp_pwin()

