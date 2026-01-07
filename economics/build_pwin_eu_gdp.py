#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build pwin_eu_gdp.csv
--------------------
EU GDP – Markov bins
P(outcome | state) with shrinkage
"""

import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "event_states_eu_gdp.csv"
OUT_FILE = DATA_DIR / "pwin_eu_gdp.csv"

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OUTCOMES = ["EXPANSION", "MODERATE", "STALL", "CONTRACTION"]
SHRINK_K = 20   # same philosophy as US GDP


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def shrink(p: float, n: int, k: int = SHRINK_K) -> float:
    """
    Empirical Bayes shrinkage towards uniform prior
    """
    prior = 1 / len(OUTCOMES)
    return (p * n + prior * k) / (n + k)


# ─────────────────────────────────────────────
# CORE
# ─────────────────────────────────────────────
def build_pwin():

    df = pd.read_csv(IN_FILE)

    rows = []

    for state, g in df.groupby("state"):
        n = len(g)

        for outcome in OUTCOMES:
            wins = (g["outcome"] == outcome).sum()
            p_raw = wins / n if n > 0 else 1 / len(OUTCOMES)
            p = shrink(p_raw, n)

            rows.append({
                "state": state,
                "outcome": outcome,
                "samples": n,
                "wins": int(wins),
                "p_raw": round(p_raw, 4),
                "p_shrunk": round(p, 4),
            })

    out = (
        pd.DataFrame(rows)
        .sort_values(["state", "p_shrunk"], ascending=[True, False])
        .reset_index(drop=True)
    )

    out.to_csv(OUT_FILE, index=False)

    print(f"✔ EU GDP pwin written: {OUT_FILE}")
    print(out.head(12))


# ─────────────────────────────────────────────
if __name__ == "__main__":
    build_pwin()

