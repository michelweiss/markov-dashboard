#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────
# Forward Returns erzeugen
# ─────────────────────────────────────────────────────────────

def make_forward_returns(close: pd.Series, horizons=(20, 60, 120)):
    df = pd.DataFrame(index=close.index)

    for h in horizons:
        df[f"fwd_ret_{h}"] = close.pct_change(h).shift(-h)

    return df


# ─────────────────────────────────────────────────────────────
# Information Coefficient (Spearman)
# ─────────────────────────────────────────────────────────────

def information_coefficient(alpha: pd.Series, future_ret: pd.Series):
    df = pd.concat([alpha, future_ret], axis=1).dropna()
    if len(df) < 30:
        return np.nan
    return df.corr(method="spearman").iloc[0, 1]


# ─────────────────────────────────────────────────────────────
# Hit Rate
# ─────────────────────────────────────────────────────────────

def hit_rate(alpha: pd.Series, future_ret: pd.Series):
    df = pd.concat([alpha, future_ret], axis=1).dropna()

    correct = np.sign(df.iloc[:, 0]) == np.sign(df.iloc[:, 1])
    return correct.mean() if len(correct) > 0 else np.nan


# ─────────────────────────────────────────────────────────────
# Conditional Return bei Z-Threshold
# ─────────────────────────────────────────────────────────────

def conditional_return(alpha_z: pd.Series, future_ret: pd.Series, z_thr=1.0):
    df = pd.concat([alpha_z, future_ret], axis=1).dropna()
    df = df[df.iloc[:, 0] > z_thr]
    return df.iloc[:, 1].mean() if not df.empty else np.nan


# ─────────────────────────────────────────────────────────────
# Rolling IC Stability
# ─────────────────────────────────────────────────────────────

def rolling_ic(alpha: pd.Series, future_ret: pd.Series, window=120):
    """
    Rolling Spearman IC – vollständig pandas-version-robust
    """
    df = pd.concat([alpha, future_ret], axis=1).dropna()
    df.columns = ["alpha", "fwd"]

    if len(df) < window:
        return pd.Series(index=df.index, dtype=float)

    ic_vals = []
    ic_idx  = []

    for i in range(window, len(df)):
        sub = df.iloc[i-window:i]

        # ✅ Spearman manuell berechnet (über Ränge)
        ic = sub["alpha"].rank().corr(sub["fwd"].rank())
        ic_vals.append(ic)
        ic_idx.append(df.index[i])

    return pd.Series(ic_vals, index=ic_idx)

# ─────────────────────────────────────────────────────────────
# MASTER VALIDATOR
# ─────────────────────────────────────────────────────────────

def validate_alpha_forward(
    alpha_df: pd.DataFrame,
    close: pd.Series,
    alpha_col="alpha",
    alpha_z_col="alpha_z_main",
    horizons=(20, 60, 120),
    z_thr=1.0
):
    """
    Erwartet:
    - alpha_df mit Index = Datum
    - Spalten: alpha_col, alpha_z_col
    - close: Asset Close Serie
    """

    fwd = make_forward_returns(close, horizons)

    df = alpha_df.join(fwd, how="inner")

    results = {}

    for h in horizons:
        fwd_col = f"fwd_ret_{h}"

        alpha   = df[alpha_col]
        alpha_z = df[alpha_z_col]
        fwd_ret = df[fwd_col]

        results[h] = {
            "IC": information_coefficient(alpha, fwd_ret),
            "HitRate": hit_rate(alpha, fwd_ret),
            "CondRet_Z_GT_1": conditional_return(alpha_z, fwd_ret, z_thr),
            "IC_Series": rolling_ic(alpha, fwd_ret)
        }

    return results

