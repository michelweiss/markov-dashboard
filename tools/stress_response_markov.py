#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
# PATH PATCH
# ─────────────────────────────────────────────
MARKOV_ROOT = Path(__file__).resolve().parents[1]
if str(MARKOV_ROOT) not in sys.path:
    sys.path.insert(0, str(MARKOV_ROOT))

from tools.prices_eodhd import tool_prices
import tools.markov_core_v3 as mc3


# ─────────────────────────────────────────────
# CORE FUNCTION
# ─────────────────────────────────────────────

def compute_stress_response(
    prices: pd.Series,
    freq: str = "weekly",
    sigma_window: int = 52,
) -> dict:

    df = prices.to_frame("Close")
    df = mc3.preprocess_prices(df, freq=freq)

    if df is None or df.empty or len(df) < sigma_window + 10:
        return {}

    # Returns & Volatility
    ret = df["Close"].pct_change()
    vol = ret.rolling(sigma_window).std()

    stress_1 = ret <= -1.0 * vol
    stress_2 = ret <= -2.0 * vol

    _, p_up = mc3.calc_transitions(df)
    if p_up is None or p_up.empty:
        return {}

    def mean_after(mask):
        idx = mask.shift(1).fillna(False)
        return float(p_up[idx].mean()) if idx.any() else np.nan

    return {
        "p_up_normal": float(p_up.mean()),
        "p_up_after_-1sigma": mean_after(stress_1),
        "p_up_after_-2sigma": mean_after(stress_2),
        "stress_delta_1sigma": mean_after(stress_1) - float(p_up.mean()),
        "stress_delta_2sigma": mean_after(stress_2) - float(p_up.mean()),
    }


# ─────────────────────────────────────────────
# RUN FOR T1_CORE
# ─────────────────────────────────────────────

if __name__ == "__main__":

    # 👉 manuell aus Phase 1A übernommen
    CORE_TICKERS = ["AAPL", "WBD", "NVDA"]

    rows = []

    for tk in CORE_TICKERS:
        print(f"🔎 Stress analysis for {tk}")
        px = tool_prices(tk, start="2018-01-01")

        if isinstance(px, pd.DataFrame):
            for c in ["adjclose", "Adj Close", "close", "Close"]:
                if c in px.columns:
                    px = px[c]
                    break
            else:
                px = px.iloc[:, -1]

        px.index = pd.to_datetime(px.index)
        px = px.sort_index()

        res = compute_stress_response(px)
        if not res:
            continue

        res["Ticker"] = tk
        rows.append(res)

    df_out = pd.DataFrame(rows).set_index("Ticker")

    print("\n📉 STRESS RESPONSE (Weekly)")
    print(df_out.round(3))

    out_fp = MARKOV_ROOT / "data" / "snapshots" / "stress_response_t1_core.csv"
    df_out.to_csv(out_fp)
    print(f"\n💾 Saved to {out_fp}")

