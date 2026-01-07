#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
#  Trend-Matrix Extension · Legacy Version (kompatibel zu alten Screenern)
#  - Liefert p_up_* Felder + LastClose
#  - Stellt sicher: Ret1W%, Ret4W%, Ret1M% sind vorhanden (aus Close berechnet)
# ------------------------------------------------------------------

import pandas as pd
import numpy as np

def _ensure_compat_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Sorgt dafür, dass Ret1W%, Ret4W%, Ret1M% vorhanden sind."""
    if df is None or df.empty:
        return df
    out = df.copy()

    # Close muss vorhanden sein, sonst können wir nichts berechnen
    if "Close" not in out.columns:
        return out

    # Falls bereits vorhanden: nichts überschreiben
    if "Ret1W%" not in out.columns:
        out["Ret1W%"] = out["Close"].pct_change(5) * 100
    if "Ret4W%" not in out.columns:
        out["Ret4W%"] = out["Close"].pct_change(20) * 100
    if "Ret1M%" not in out.columns:
        # 21 Handelstage als Monatsnäherung
        out["Ret1M%"] = out["Close"].pct_change(21) * 100

    return out


def create_trend_matrix(dfs: dict, threshold_func=None) -> pd.DataFrame:
    """
    Erwartet dict {ticker: df} mit Preis- und (optional) p_up-Spalten.
    Gibt DataFrame mit:
      - p_up_daily / p_up_week / p_up_month (falls vorhanden, sonst p_up fallback)
      - LastClose
      - Ret1W%, Ret4W%, Ret1M% (immer vorhanden, aus Close berechnet falls nötig)
      - p_up_meta (Durchschnitt der p_up-Spalten, wenn vorhanden)
    """
    if not dfs:
        return pd.DataFrame()

    records = []
    for tk, df in dfs.items():
        if df is None or df.empty:
            continue

        df = _ensure_compat_cols(df)

        rec = {"Ticker": tk}

        # p_up-Spalten einsammeln (legacy-kompatibel)
        # Falls du nur eine p_up hast, verwende sie als Fallback für die anderen
        p_up_daily = None
        p_up_week  = None
        p_up_month = None

        # Suche bekannte Varianten
        # (wir sind tolerant bei Schreibweisen)
        cols_lower = {c.lower(): c for c in df.columns}

        def last_or_nan(colname):
            return float(df[colname].dropna().iloc[-1]) if colname in df.columns and not df[colname].dropna().empty else np.nan

        # 1) exakte/sprachliche Varianten finden
        for key, target in [
            ("p_up_daily", "p_up_daily"),
            ("p_up_week",  "p_up_week"),
            ("p_up_month", "p_up_month"),
            ("p_up",       "p_up"),  # generisches p_up
        ]:
            if key in cols_lower:
                cname = cols_lower[key]
                val = last_or_nan(cname)
                if target == "p_up_daily": p_up_daily = val
                if target == "p_up_week":  p_up_week  = val
                if target == "p_up_month": p_up_month = val
                if target == "p_up":
                    # Fallback: wenn nur p_up vorhanden, nutze sie für fehlende Frequenzen
                    if p_up_daily is None: p_up_daily = val
                    if p_up_week  is None: p_up_week  = val
                    if p_up_month is None: p_up_month = val

        rec["p_up_daily"] = p_up_daily
        rec["p_up_week"]  = p_up_week
        rec["p_up_month"] = p_up_month

        # LastClose
        rec["LastClose"] = float(df["Close"].dropna().iloc[-1]) if "Close" in df.columns and not df["Close"].dropna().empty else np.nan

        # Kompatible Return-Prozente – SICHER befüllen
        rec["Ret1W%"] = last_or_nan("Ret1W%") if "Ret1W%" in df.columns else np.nan
        rec["Ret4W%"] = last_or_nan("Ret4W%") if "Ret4W%" in df.columns else np.nan
        rec["Ret1M%"] = last_or_nan("Ret1M%") if "Ret1M%" in df.columns else np.nan

        # Falls aus irgendeinem Grund noch NaN: aus Close ad hoc berechnen
        if np.isnan(rec["Ret1W%"]) and "Close" in df.columns:
            rec["Ret1W%"] = float((df["Close"].pct_change(5) * 100).dropna().iloc[-1]) if not (df["Close"].pct_change(5)*100).dropna().empty else np.nan
        if np.isnan(rec["Ret4W%"]) and "Close" in df.columns:
            rec["Ret4W%"] = float((df["Close"].pct_change(20) * 100).dropna().iloc[-1]) if not (df["Close"].pct_change(20)*100).dropna().empty else np.nan
        if np.isnan(rec["Ret1M%"]) and "Close" in df.columns:
            rec["Ret1M%"] = float((df["Close"].pct_change(21) * 100).dropna().iloc[-1]) if not (df["Close"].pct_change(21)*100).dropna().empty else np.nan

        records.append(rec)

    trend_df = pd.DataFrame(records).set_index("Ticker")

    # p_up_meta: Durchschnitt über die vorhandenen p_up-Frequenzen
    p_cols = [c for c in ["p_up_daily", "p_up_week", "p_up_month"] if c in trend_df.columns]
    if p_cols:
        trend_df["p_up_meta"] = trend_df[p_cols].mean(axis=1)
    else:
        trend_df["p_up_meta"] = np.nan

    # Sicherstellen, dass Ret4W% existiert (zur Sicherheit, falls records leer)
    for c in ["Ret1W%", "Ret4W%", "Ret1M%"]:
        if c not in trend_df.columns:
            trend_df[c] = np.nan

    return trend_df

