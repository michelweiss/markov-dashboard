#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build CPI → DXY reaction statistics
----------------------------------
Baseline reaction (no regime split yet)
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

CPI_FILE = DATA_DIR / "macro_actuals.csv"
FX_FILE  = DATA_DIR / "dxy_returns.csv"
OUT_FILE = DATA_DIR / "reaction_stats_fx.csv"


def build_reaction_stats_fx():

    cpi = pd.read_csv(CPI_FILE, parse_dates=["date"])
    fx  = pd.read_csv(FX_FILE,  parse_dates=["date"])

    df = pd.merge(cpi, fx, on="date", how="inner")
    if df.empty:
        raise RuntimeError("No overlapping CPI/DXY dates found")

    df["usd_up"] = (df["ret_1d"] > 0).astype(int)
    df["cpi_surprise_up"] = df["surprise"] > 0

    rows = []
    for outcome, g in df.groupby("cpi_surprise_up"):
        n = len(g)
        rows.append({
            "cpi_surprise_up": bool(outcome),
            "samples": int(n),
            "p_usd_up": round(g["usd_up"].mean(), 3),
            "avg_ret_1d": round(g["ret_1d"].mean() * 100, 2),
        })

    out = pd.DataFrame(rows).sort_values("cpi_surprise_up", ascending=False)
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ FX reaction stats written: {OUT_FILE}")
    print(out)


if __name__ == "__main__":
    build_reaction_stats_fx()

