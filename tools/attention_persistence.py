#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# tools/attention_persistence.py

import pandas as pd
import numpy as np
from typing import Literal

def compute_attention_persistence(
    df: pd.DataFrame,
    freq: Literal["weekly", "monthly"] = "weekly",
    top_k: int = 10,
    window: int = 12,
    weighted: bool = False,
) -> pd.DataFrame:
    """
    Berechnet Attention Persistence (AP) aus Snapshot-DF.
    Erwartet Spalten: date, Ticker, p_up, rank
    """

    req = {"Ticker", "rank"}
    if not req.issubset(df.columns):
        raise ValueError(f"DF muss Spalten {req} enthalten")

    out = df.copy()
    out = out.sort_values(["Ticker", "date"])

    # Attention Flag
    out["attention"] = (out["rank"] <= top_k).astype(int)

    if weighted:
        # Rank-Gewicht: 1.0 (Rank 1) → 0.0 (Rank K)
        out["rank_weight"] = np.clip(
            1.0 - (out["rank"] - 1) / max(top_k - 1, 1),
            0.0,
            1.0
        )
        out["att_weighted"] = out["attention"] * out["rank_weight"]
        base_col = "att_weighted"
    else:
        base_col = "attention"

    # Rolling AP pro Ticker
    min_p = window if freq == "weekly" else 1

    out["ap_score"] = (
        out
        .groupby("Ticker")[base_col]
        .rolling(window=window, min_periods=min_p)
        .mean()
        .reset_index(level=0, drop=True)
    )
    

    # Eligibility Flag
    out["is_persistent"] = out["ap_score"] >= 0.6

    return out

