#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build CPI → US10Y reaction statistics
------------------------------------
Baseline reaction (no regime split)
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

CPI_FILE  = DATA_DIR / "macro_actuals.csv"
BOND_FILE = DATA_DIR / "us10y_yield.csv"
OUT_FILE  = DATA_DIR / "reaction_stats_bonds.csv"


def build_reaction_stats_bonds():

    cpi  = pd.read_csv(CPI_FILE,  parse_dates=["date"])
    bond = pd.read_csv(BOND_FILE, parse_dates=["date"])

    df = pd.merge(cpi, bond, on="date", how="inner")
    if df.empty:
        raise RuntimeError("No overlapping CPI/US10Y dates found")

    df["yield_up"] = (df["d_yield_bp"] > 0).astype(int)
    df["cpi_surprise_up"] = df["surprise"] > 0

    rows = []
    for outcome, g in df.groupby("cpi_surprise_up"):
        n = len(g)
        rows.append({
            "cpi_surprise_up": bool(outcome),
            "samples": int(n),
            "p_yield_up": round(g["yield_up"].mean(), 3),
            "avg_d_yield_bp": round(g["d_yield_bp"].mean(), 2),
        })

    out = pd.DataFrame(rows).sort_values("cpi_surprise_up", ascending=False)
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ Bond reaction stats written: {OUT_FILE}")
    print(out)


if __name__ == "__main__":
    build_reaction_stats_bonds()

