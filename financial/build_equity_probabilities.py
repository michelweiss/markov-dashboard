#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build Equity Index Probabilities (rolling d / w / m)
----------------------------------------------------
• Daily   : rolling 1 trading day (t-2 → t-1 implizit)
• Weekly  : rolling 5 trading days
• Monthly : rolling 21 trading days
• Uses Markov Core v4 (rolling-first)
"""

# ------------------------------------------------------------
# PATH PATCH – find Markov root
# ------------------------------------------------------------
import sys
from pathlib import Path
from datetime import date
import json

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
from financial.indices_config import INDICES
from tools.prices_eodhd import tool_prices
from tools.markov_core_v4 import rolling_p_up_last

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
def build_equity_probabilities(freq: str):
    window = WINDOWS[freq]

    payload = {
        "frequency": freq,
        "as_of": date.today().isoformat(),
        "indices": {},
    }

    for key, cfg in INDICES.items():
        ticker = cfg["ticker"]

        # 1) Load DAILY prices
        df = tool_prices(
            ticker=ticker,
            start=START_DATE,
            adjusted=True,
        )

        if df is None or len(df) < MIN_BARS:
            print(f"⚠️  {ticker}: insufficient data")
            continue

        df = df.sort_index()

        # 2) Rolling Markov p_up (v4)
        p_up, n = rolling_p_up_last(
            df_raw=df,
            freq=freq,
            horizon=WINDOWS[freq],
            return_n=True,
        )


        if p_up != p_up:
            continue

        payload["indices"][key] = {
            "label": cfg["label"],
            "region": cfg["region"],
            "ticker": ticker,
            "p_up": round(float(p_up), 4),
            "n_samples": int(n),
        }


    # 3) Persist snapshot
    out_file = OUT_DIR / f"equity_probabilities_{freq}.json"
    with open(out_file, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"✔ equity probabilities written: {out_file}")

# ------------------------------------------------------------
# RUNNER
# ------------------------------------------------------------
if __name__ == "__main__":
    for freq in ("daily", "weekly", "monthly"):
        build_equity_probabilities(freq)

