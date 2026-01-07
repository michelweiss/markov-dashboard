#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build VIX Probabilities (rolling d / w / m)
-------------------------------------------
• Input    : VIX
• Transform: vix_inv = -log(VIX)
• Daily    : rolling 1 trading day
• Weekly   : rolling 5 trading days
• Monthly  : rolling 21 trading days
• Uses Markov Core v4 (rolling-first)
• Style IDENTICAL to build_equity_probabilities.py
"""

# ------------------------------------------------------------
# PATH PATCH – find Markov root
# ------------------------------------------------------------
import sys
from pathlib import Path
from datetime import date
import json
import numpy as np
import pandas as pd

def find_markov_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if p.name == "Markov":
            return p
    raise RuntimeError("❌ Markov root directory not found")

MARKOV_ROOT = find_markov_root(Path(__file__).resolve())
if str(MARKOV_ROOT) not in sys.path:
    sys.path.insert(0, str(MARKOV_ROOT))

# ------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------
from tools.prices_eodhd import tool_prices
from tools.markov_core_v4 import rolling_p_up_last, preprocess_prices
from financial.vix_config import VIX

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
START_DATE = "2015-01-01"
MIN_BARS   = 250

OUT_DIR = MARKOV_ROOT / "financial" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOWS = {
    "daily": 1,
    "weekly": 5,
    "monthly": 21,
}

# ------------------------------------------------------------
# CORE
# ------------------------------------------------------------
def build_vix_probabilities(freq: str):
    payload = {
        "frequency": freq,
        "as_of": date.today().isoformat(),
        "indices": {},
    }

    for key, cfg in VIX.items():
        ticker = cfg["ticker"]

        # 1) Load DAILY prices (adjusted)
        df = tool_prices(
            ticker=ticker,
            start=START_DATE,
            adjusted=True,
        )

        if df is None or len(df) < MIN_BARS:
            print(f"⚠️  {ticker}: insufficient data")
            continue

        # 2) Normalize prices EXACTLY like Markov Core
        df = preprocess_prices(df)

        if df.empty or "Close" not in df.columns:
            print(f"⚠️  {ticker}: no Close after normalization")
            continue

        df = df.sort_index()

        # 3) Invert VIX → Risk-On semantics
        vix_inv = -np.log(df["Close"])
        vix_df  = pd.DataFrame({"Close": vix_inv}).dropna()

        if len(vix_df) < MIN_BARS:
            print(f"⚠️  {ticker}: insufficient data after transform")
            continue

        # 4) Rolling Markov p_up (v4) – IDENTISCH zu Equity & Credit
        p_up, n = rolling_p_up_last(
            df_raw=vix_df,
            freq=freq,
            horizon=WINDOWS[freq],
            return_n=True,
        )

        if p_up != p_up:  # NaN-Check
            continue

        payload["indices"][key] = {
            "label": cfg["label"],
            "region": cfg["region"],
            "ticker": ticker,
            "p_up": round(float(p_up), 4),
            "n_samples": int(n),
        }

    # 5) Persist snapshot
    out_file = OUT_DIR / f"vix_probabilities_{freq}.json"
    with open(out_file, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"✔ vix probabilities written: {out_file}")

# ------------------------------------------------------------
# RUNNER
# ------------------------------------------------------------
if __name__ == "__main__":
    for freq in ("daily", "weekly", "monthly"):
        build_vix_probabilities(freq)

