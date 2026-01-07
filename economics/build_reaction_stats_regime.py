#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build CPI → SPX reaction statistics with regime split
-----------------------------------------------------
Regime:
    Risk-On  = SPX > SMA200
    Risk-Off = SPX <= SMA200
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
OUT_FILE = DATA_DIR / "reaction_stats_regime.csv"


def build_reaction_stats_regime():

    cpi = pd.read_csv(CPI_FILE, parse_dates=["date"])
    spx = pd.read_csv(SPX_FILE, parse_dates=["date"])

    # --- merge
    df = pd.merge(cpi, spx, on="date", how="inner")
    if df.empty:
        raise RuntimeError("No overlapping CPI/SPX dates found")

    # --- pick price column robustly
    price_col = None
    for cand in ("price", "adjusted_close", "close", "adj_close"):
        if cand in df.columns:
            price_col = cand
            break
    if price_col is None:
        raise RuntimeError(f"No price column found. Columns: {list(df.columns)}")

    # --- SMA200 regime
    df = df.sort_values("date").reset_index(drop=True)
    df["sma200"] = df[price_col].rolling(200).mean()
    df["regime"] = (df[price_col] > df["sma200"]).map(
        {True: "Risk-On", False: "Risk-Off"}
    )

    # --- market direction
    df["spx_up"] = (df["ret_1d"] > 0).astype(int)
    df["cpi_surprise_up"] = df["surprise"] > 0

    rows = []

    for (outcome, regime), g in df.groupby(
        ["cpi_surprise_up", "regime"]
    ):
        n = len(g)
        if n < 10:
            continue

        rows.append({
            "cpi_surprise_up": bool(outcome),
            "regime": regime,
            "samples": int(n),
            "p_spx_up": round(g["spx_up"].mean(), 3),
            "avg_ret_1d": round(g["ret_1d"].mean() * 100, 2),
        })

    out = pd.DataFrame(rows).sort_values(
        ["cpi_surprise_up", "regime"],
        ascending=[False, True]
    )

    out.to_csv(OUT_FILE, index=False)

    print(f"✔ Reaction stats (regime) written: {OUT_FILE}")
    print(out)


if __name__ == "__main__":
    build_reaction_stats_regime()

