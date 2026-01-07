#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build pwin_ecb.csv
------------------
P(outcome | state) with shrinkage
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "event_states_ecb.csv"
OUT_FILE = DATA_DIR / "pwin_ecb.csv"

SHRINK_K = 10   # stronger shrink (small samples)


def shrink(p: float, n: int, k: int = SHRINK_K) -> float:
    return (p * n + (1 / 3) * k) / (n + k)


def build_pwin():

    df = pd.read_csv(IN_FILE)

    rows = []

    for state, g in df.groupby("state"):   # ✅ FIX
        n = len(g)

        for outcome in ["CUT", "HOLD", "HIKE"]:
            wins = (g["outcome"] == outcome).sum()
            p_raw = wins / n if n > 0 else 1 / 3
            p = shrink(p_raw, n)

            rows.append({
                "state": state,            # bleibt String "(1,)"
                "outcome": outcome,
                "samples": n,
                "wins": wins,
                "p_raw": round(p_raw, 3),
                "p_shrunk": round(p, 3),
            })

    out = (
        pd.DataFrame(rows)
        .sort_values(["state", "p_shrunk"], ascending=[True, False])
        .reset_index(drop=True)
    )

    out.to_csv(OUT_FILE, index=False)

    print(f"✔ ECB pwin written: {OUT_FILE}")
    print(out)



if __name__ == "__main__":
    build_pwin()

