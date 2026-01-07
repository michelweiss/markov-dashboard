#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
#  Trend Matrix Extension – Multi-Frequency + Meta-Fusion (stable)
#  Michel Weiss · 2025-10-27
# ------------------------------------------------------------------

import os, sys
import pandas as pd
import numpy as np

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(FILE_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from markov_core_v1 import calc_transitions, compute_returns
except ModuleNotFoundError:
    from tools.markov_core_v1 import calc_transitions, compute_returns


# ============================================================
#  Hilfsfunktion: robustes calc_transitions-Handling
# ============================================================
def _safe_calc(df):
    """Verarbeitet sowohl alte (dict) als auch neue (tuple) Rückgaben."""
    try:
        result = calc_transitions(df)
        if isinstance(result, dict):
            trans = result
            p_up = np.mean([v["1"] for v in trans.values()])
        elif isinstance(result, tuple) and len(result) == 3:
            trans, _, p_up = result
        else:
            raise ValueError("Unexpected format from calc_transitions()")
        return p_up
    except Exception as e:
        print(f"⚠️ Fehler bei calc_transitions(): {e}")
        return np.nan


# ============================================================
#  Hauptfunktion
# ============================================================
def create_trend_matrix(dfs: dict, threshold_func=None):
    """
    Berechnet p_up für daily, weekly, monthly + p_up_meta für alle Ticker.
    """
    records = []

    for tk, df in dfs.items():
        if df is None or df.empty or "Close" not in df.columns:
            continue

        df = compute_returns(df)

        # --- Frequenzen vorbereiten ---
        freq_map = {
            "daily": df,
            "weekly": df.resample("W-FRI").last(),
            "monthly": df.resample("M").last()
        }

        p_up_daily = _safe_calc(freq_map["daily"])
        p_up_week = _safe_calc(freq_map["weekly"])
        p_up_month = _safe_calc(freq_map["monthly"])

        # --- Meta-Mittelwert ---
        vals = [v for v in [p_up_daily, p_up_week, p_up_month] if pd.notna(v)]
        p_up_meta = np.mean(vals) if vals else np.nan

        # --- next_ret-Fallback ---
        next_ret = df["next_ret"].iloc[-2] if "next_ret" in df.columns else np.nan

        rec = {
            "Ticker": tk,
            "p_up_daily": p_up_daily,
            "p_up_week": p_up_week,
            "p_up_month": p_up_month,
            "p_up_meta": p_up_meta,
            "next_ret": float(next_ret) if pd.notna(next_ret) else np.nan,
            "Ret1W%": float(next_ret) * 100 if pd.notna(next_ret) else 0.0,
            "Ret4W%": float(next_ret) * 100 if pd.notna(next_ret) else 0.0,
            "Ret1M%": float(next_ret) * 100 if pd.notna(next_ret) else 0.0
        }

        if threshold_func:
            try:
                thr = threshold_func(df)
                rec["AboveThr"] = p_up_meta >= thr
            except Exception:
                rec["AboveThr"] = np.nan
        else:
            rec["AboveThr"] = np.nan

        records.append(rec)

    trend_df = pd.DataFrame.from_records(records)
    if trend_df.empty:
        return pd.DataFrame()

    # --- TripleConfirm-Logik ---
    trend_df["TripleConfirmLong"] = (
        (trend_df["p_up_daily"] >= 0.55)
        & (trend_df["p_up_week"] >= 0.55)
        & (trend_df["p_up_month"] >= 0.55)
    )
    trend_df["TripleConfirmShort"] = (
        (trend_df["p_up_daily"] <= 0.45)
        & (trend_df["p_up_week"] <= 0.45)
        & (trend_df["p_up_month"] <= 0.45)
    )

    # --- Dummy-Spalten für volle Kompatibilität ---
    for c in ["BucketAvgRet%", "Cluster"]:
        if c not in trend_df.columns:
            trend_df[c] = np.nan

    return trend_df

