#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build pwin_eu_cpi.csv
--------------------
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "event_states_eu_cpi.csv"
OUT_FILE = DATA_DIR / "pwin_eu_cpi.csv"

SHRINK_K = 20


def shrink(p, n, k=SHRINK_K):
    return (p * n + 0.5 * k) / (n + k)


def build_pwin():

    df = pd.read_csv(IN_FILE)

    rows = []

    for state, g in df.groupby("state"):
        n = len(g)

        for outcome in ["ABOVE", "BELOW"]:
            wins = (g.outcome == outcome).sum()
            p_raw = wins / n if n else 0.5
            p = shrink(p_raw, n)

            rows.append({
                "state": state,
                "outcome": outcome,
                "samples": n,
                "p_raw": round(p_raw, 3),
                "p_shrunk": round(p, 3),
            })

    out = pd.DataFrame(rows)
    out.to_csv(OUT_FILE, index=False)
    print(f"✔ EU CPI pwin written: {OUT_FILE}")


if __name__ == "__main__":
    build_pwin()

