#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build CPI → SPX reaction statistics
-----------------------------------
Baseline reaction (no regime split yet)
"""

import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

CPI_FILE = DATA_DIR / "macro_actuals.csv"
SPX_FILE = DATA_DIR / "spx_returns.csv"
OUT_FILE = DATA_DIR / "reaction_stats.csv"


def build_reaction_stats():

    # --- load data
    cpi = pd.read_csv(CPI_FILE, parse_dates=["date"])
    spx = pd.read_csv(SPX_FILE, parse_dates=["date"])

    # --- align on date
    df = pd.merge(cpi, spx, on="date", how="inner")

    if df.empty:
        raise RuntimeError("No overlapping CPI/SPX dates found")

    # --- market direction
    df["spx_up"] = (df["ret_1d"] > 0).astype(int)

    rows = []

    # --- group by CPI outcome
    for outcome, g in df.groupby(df["surprise"] > 0):

        n = len(g)
        p_up = g["spx_up"].mean()
        avg_ret = g["ret_1d"].mean()

        rows.append({
            "cpi_surprise_up": bool(outcome),
            "samples": int(n),
            "p_spx_up": round(p_up, 3),
            "avg_ret_1d": round(avg_ret * 100, 2),  # %
        })

    out = pd.DataFrame(rows).sort_values("cpi_surprise_up", ascending=False)
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ Reaction stats written: {OUT_FILE}")
    print(out)


if __name__ == "__main__":
    build_reaction_stats()

