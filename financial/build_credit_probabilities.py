#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build Credit Probabilities (rolling d / w / m)
----------------------------------------------
• Spread = log(HYG) − log(LQD)
• Daily   : rolling 1 trading day
• Weekly  : rolling 5 trading days
• Monthly : rolling 21 trading days
• Uses Markov Core v4 (rolling-first)
• Style & Structure IDENTICAL to build_equity_probabilities.py
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
from financial.credit_config import CREDIT
from tools.prices_eodhd import tool_prices
from tools.markov_core_v4 import rolling_p_up_last
from tools.markov_core_v4 import preprocess_prices


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
def build_credit_probabilities(freq: str):
    window = WINDOWS[freq]

    payload = {
        "frequency": freq,
        "as_of": date.today().isoformat(),
        "indices": {},
    }

    for key, cfg in CREDIT.items():
        hy_ticker = cfg["tickers"]["hy"]
        ig_ticker = cfg["tickers"]["ig"]

        # 1) Load DAILY prices (adjusted, wie Equity)
        df_hy = tool_prices(
            ticker=hy_ticker,
            start=START_DATE,
            adjusted=True,
        )
        df_ig = tool_prices(
            ticker=ig_ticker,
            start=START_DATE,
            adjusted=True,
        )

        if (
            df_hy is None or df_ig is None
            or len(df_hy) < MIN_BARS
            or len(df_ig) < MIN_BARS
        ):
            print(f"⚠️  {hy_ticker}/{ig_ticker}: insufficient data")
            continue

        # 2) Align & build spread
        df_hy = preprocess_prices(df_hy)
        df_ig = preprocess_prices(df_ig)
        
        if "Close" not in df_hy.columns or "Close" not in df_ig.columns:
            print(f"⚠️  {hy_ticker}/{ig_ticker}: no Close after normalization")
            return
        
        df = (
            pd.concat(
                [
                    df_hy["Close"].rename("HY"),
                    df_ig["Close"].rename("IG"),
                ],
                axis=1,
            )
            .dropna()
            .sort_index()
        )


        if len(df) < MIN_BARS:
            continue

        spread = np.log(df["HY"]) - np.log(df["IG"])
        spread_df = pd.DataFrame({"Close": spread})

        # 3) Rolling Markov p_up (v4) – IDENTISCH zu Equity
        p_up, n = rolling_p_up_last(
            df_raw=spread_df,
            freq=freq,
            horizon=WINDOWS[freq],
            return_n=True,
        )

        if p_up != p_up:
            continue

        payload["indices"][key] = {
            "label": cfg["label"],
            "region": cfg["region"],
            "tickers": f"{hy_ticker}-{ig_ticker}",
            "p_up": round(float(p_up), 4),
            "n_samples": int(n),
        }

    # 4) Persist snapshot
    out_file = OUT_DIR / f"credit_probabilities_{freq}.json"
    with open(out_file, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"✔ credit probabilities written: {out_file}")

# ------------------------------------------------------------
# RUNNER
# ------------------------------------------------------------
if __name__ == "__main__":
    for freq in ("daily", "weekly", "monthly"):
        build_credit_probabilities(freq)

