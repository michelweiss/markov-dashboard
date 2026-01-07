#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
#  Markov Core v2 · Trader-kompatibel (dict-based transitions)
#  Final Version – mit fixem Threshold 0.55 (Long ≥ 0.55 / Short ≤ 0.45)
#  + automatische Signal-Spalte (LONG / SHORT / NEUTRAL)
#  Kompatibel mit: screener_fusion_nasdaq100.py, intraday_trader_long.py, short.py
# ------------------------------------------------------------------

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ==========================================================
# Globale Settings
# ==========================================================
AHEAD = 1
START = 100
OPT_THR_DEFAULT = 0.55   # ✅ Michel-Default: Long ≥ 0.55 / Short ≤ 0.45

# ==========================================================
# Utilities
# ==========================================================
def _normalize_close(df: pd.DataFrame) -> pd.DataFrame:
    """Sorgt für 'Close'-Spalte und DatetimeIndex."""
    if df is None or len(df) == 0:
        return pd.DataFrame()
    out = df.copy()

    if "Close" not in out.columns:
        for c in ("close", "adj_close", "Adj Close", "adjusted_close"):
            if c in out.columns:
                out = out.rename(columns={c: "Close"})
                break
    if "Close" not in out.columns:
        return pd.DataFrame()

    if not isinstance(out.index, pd.DatetimeIndex):
        if "Date" in out.columns:
            out["Date"] = pd.to_datetime(out["Date"], errors="coerce", utc=False)
            out = out.set_index("Date")
        else:
            out.index = pd.to_datetime(out.index, errors="coerce", utc=False)

    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out = out.dropna(subset=["Close"])
    return out


def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Ergänzt Returns + y_bin (idempotent)."""
    out = _normalize_close(df)
    if out.empty:
        return out
    if "Returns" not in out.columns:
        out["Returns"] = out["Close"].pct_change()
    if "y_bin" not in out.columns:
        out["y_bin"] = (out["Returns"] > 0).astype(int)
    return out


# ==========================================================
# Resampling / Preprocessing
# ==========================================================
def preprocess_prices(df_raw: pd.DataFrame, freq: str = "daily", res: str | None = None) -> pd.DataFrame:
    """Resample auf Business-Day / W-FRI / Month-End und berechnet Returns + y_bin."""
    df = _normalize_close(df_raw)
    if df.empty:
        return df

    f = (freq or "").lower()
    if f.startswith("w"):
        rule = "W-FRI"
    elif f.startswith("m"):
        rule = "M"
    elif f.startswith("d"):
        rule = "B"
    else:
        rule = res or "B"

    out = df.resample(rule).last()
    out = out.dropna(subset=["Close"]).copy()

    out["Returns"] = out["Close"].pct_change()
    out["y_bin"] = (out["Returns"] > 0).astype(int)
    out = out.dropna(subset=["Returns"])
    return out


# ==========================================================
# 3-State Markov: Transition-Schätzung (robust)
# ==========================================================
def calc_transitions(df: pd.DataFrame):
    """
    Liefert Transition-Map:
      {(y_{t-3}, y_{t-2}, y_{t-1}): {'1': p_up, '0': p_down}}
    Wenn Daten knapp sind → fallback auf globale Hit-Rate.
    """
    if df is None or len(df) < 5:
        return {}, None, None

    if "y_bin" not in df.columns:
        df = compute_returns(df)
        if "y_bin" not in df.columns:
            return {}, None, None

    y = pd.Series(df["y_bin"]).astype(int).to_numpy()
    y = y[np.isfinite(y)]

    if len(y) < 5:
        p = float(np.nanmean(y)) if len(y) else 0.5
        return { (a,b,c): {"1": p, "0": 1.0 - p} for a in (0,1) for b in (0,1) for c in (0,1) }, None, None

    trans = {}
    for i in range(3, len(y)):
        state = (int(y[i-3]), int(y[i-2]), int(y[i-1]))
        nxt = int(y[i])
        if state not in trans:
            trans[state] = {"0": 0, "1": 0}
        trans[state][str(nxt)] += 1

    global_hit = float(np.mean(y)) if len(y) else 0.5
    for s in [(a,b,c) for a in (0,1) for b in (0,1) for c in (0,1)]:
        if s in trans:
            tot = trans[s]["0"] + trans[s]["1"]
            if tot > 0:
                trans[s]["1"] = trans[s]["1"] / tot
                trans[s]["0"] = 1.0 - trans[s]["1"]
            else:
                trans[s] = {"1": global_hit, "0": 1.0 - global_hit}
        else:
            trans[s] = {"1": global_hit, "0": 1.0 - global_hit}

    return trans, None, None


def _p_up_last(df: pd.DataFrame) -> float:
    """p_up des letzten beobachteten Zustands; fallback auf globale Hit-Rate / 0.5."""
    if df is None or df.empty:
        return 0.5
    df = compute_returns(df)
    if "y_bin" not in df.columns or len(df["y_bin"]) < 3:
        p = float(df["y_bin"].mean()) if "y_bin" in df.columns and len(df["y_bin"]) else 0.5
        return p if np.isfinite(p) else 0.5

    trans, _, _ = calc_transitions(df)
    last3 = tuple(int(x) for x in df["y_bin"].tail(3).to_list())
    p = trans.get(last3, {"1": 0.5}).get("1", 0.5)
    return float(p) if np.isfinite(p) else 0.5


# ==========================================================
# Variance Ratio (einfach, robust)
# ==========================================================
def _variance_ratio_simple(df_daily: pd.DataFrame) -> float:
    try:
        d = compute_returns(df_daily)
        r_d = d["Returns"].dropna()
        if len(r_d) < 30:
            return np.nan
        w = d.resample("W-FRI").last()
        r_w = w["Close"].pct_change().dropna()
        if len(r_w) < 6:
            return np.nan
        vr = (r_w.var(ddof=1)) / (r_d.var(ddof=1) * 5.0)
        return float(vr) if np.isfinite(vr) else np.nan
    except Exception:
        return np.nan


# ==========================================================
# TrendMatrix: immer alle Skalen + Threshold + Signal-Spalte
# ==========================================================
def create_trend_matrix_all(
    dfs: dict[str, pd.DataFrame],
    threshold_func=None,
    include_regime: bool = True,
) -> pd.DataFrame:
    """Baut eine Matrix mit p_up_daily, p_up_week, p_up_month, VR & Signal."""
    rows = []
    for tk, raw in (dfs or {}).items():
        base = _normalize_close(raw)
        if base.empty:
            continue

        d_d = preprocess_prices(base, "daily")
        d_w = preprocess_prices(base, "weekly")
        d_m = preprocess_prices(base, "monthly")

        p_d = _p_up_last(d_d) if not d_d.empty else np.nan
        p_w = _p_up_last(d_w) if not d_w.empty else np.nan
        p_m = _p_up_last(d_m) if not d_m.empty else np.nan

        thr = OPT_THR_DEFAULT
        if threshold_func is not None:
            try:
                df_thr = d_w if not d_w.empty else (d_d if not d_d.empty else d_m)
                thr = float(threshold_func(df_thr)) if df_thr is not None and not df_thr.empty else OPT_THR_DEFAULT
            except Exception:
                thr = OPT_THR_DEFAULT

        row = {
            "Ticker": tk,
            "p_up_daily": p_d,
            "p_up_week":  p_w,
            "p_up_month": p_m,
            "Threshold":  thr,
        }

        if include_regime:
            row["VR"] = _variance_ratio_simple(d_d if not d_d.empty else base)

        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=[
            "p_up_daily","p_up_week","p_up_month","Threshold","VR","Signal"
        ]).set_index(pd.Index([], name="Ticker"))

    df = pd.DataFrame(rows).set_index("Ticker")

    # 🧭 Automatische Signal-Spalte
    if "p_up_week" in df.columns:
        df["Signal"] = np.select(
            [
                df["p_up_week"] >= df["Threshold"],          # Long
                df["p_up_week"] <= (1 - df["Threshold"])     # Short
            ],
            ["LONG", "SHORT"],
            default="NEUTRAL"
        )
    else:
        df["Signal"] = "NEUTRAL"

    return df


def create_trend_matrix(
    dfs: dict[str, pd.DataFrame],
    threshold_func=None,
    freq: str = "weekly",
    include_regime: bool = False,
) -> pd.DataFrame:
    """Wrapper für alte Signatur: behält alle p_up-Spalten (daily/week/month)."""
    return create_trend_matrix_all(dfs, threshold_func=threshold_func, include_regime=include_regime)


# ==========================================================
# Helper (Kompatibilität)
# ==========================================================
def normalize_state_tuple(state):
    """Sorgt für 3er-Tuple (ints 0/1)."""
    try:
        a, b, c = state
        return (int(a), int(b), int(c))
    except Exception:
        return (0, 0, 0)

