#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
#  Markov Core v1 · 3-State Version (mit Trend-Matrix)
#  Kompatibel mit Screenern & Intraday-Tradern
# ------------------------------------------------------------------

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

AHEAD = 1
START = 100


# =========================================================
# Preisaufbereitung (Resampling + Cleaning)
# =========================================================
def preprocess_prices(df_raw: pd.DataFrame, freq: str = "daily", res: str = None) -> pd.DataFrame:
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df.index = pd.to_datetime(df.index, utc=True, errors="coerce").tz_localize(None)

    rule = {"daily": "D", "weekly": "W-FRI", "monthly": "M"}.get(freq.lower())
    if not rule:
        raise ValueError(f"Invalid frequency: {freq}")

    try:
        out = df.resample(rule).last()
    except Exception:
        out = df.copy()

    if "Close" not in out.columns:
        for c in ["close", "adj_close", "Adj Close"]:
            if c in out.columns:
                out.rename(columns={c: "Close"}, inplace=True)
                break

    out = out.dropna(subset=["Close"])
    return out


# =========================================================
# Returns-Berechnung
# =========================================================
def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    if "Close" not in df.columns:
        raise ValueError("❌ compute_returns() erwartet Spalte 'Close'")

    df["Returns"]  = df["Close"].pct_change()
    df["y_bin"]    = (df["Returns"] > 0).astype(int)
    df["next_ret"] = df["Returns"].shift(-1)
    df["Ret1W%"]   = df["Close"].pct_change(5) * 100
    df["Ret4W%"]   = df["Close"].pct_change(20) * 100
    df["Ret1M%"]   = df["Close"].pct_change(21) * 100
    return df


# =========================================================
# Markov-Übergänge (3-State Modell) – Trader-kompatible Version
# =========================================================
def calc_transitions(df: pd.DataFrame, ahead: int = AHEAD, verbose: bool = False):
    """
    Berechnet Übergangswahrscheinlichkeiten für 3-State-Markov-Kette:
        (y_{t-3}, y_{t-2}, y_{t-1}) → {"0": p_down, "1": p_up}

    Rückgabe:
        transitions: Dict[(int,int,int)] = {"0": float, "1": float}
    """
    if df is None or df.empty or "y_bin" not in df.columns:
        return {}

    y = df["y_bin"].fillna(0).astype(int).to_numpy()
    n = len(y)
    if n < 4:
        return {}

    transitions = {}
    for i in range(3, n):
        state = (int(y[i-3]), int(y[i-2]), int(y[i-1]))
        nxt = int(y[i])
        if state not in transitions:
            transitions[state] = {"0": 0, "1": 0}
        transitions[state][str(nxt)] += 1

    # Normalisierung
    for k, v in transitions.items():
        total = v["0"] + v["1"]
        if total > 0:
            v["0"] = v["0"] / total
            v["1"] = v["1"] / total
        else:
            v["0"], v["1"] = 0.5, 0.5

    # Optional: Debug-Info
    if verbose:
        mean_up = np.mean([v["1"] for v in transitions.values()]) if transitions else np.nan
        print(f"[calc_transitions] n={n}, states={len(transitions)}, mean(p_up)={mean_up:.3f}")

    return transitions



# =========================================================
# Trend-Matrix-Erweiterung (Daily / Weekly / Monthly)
# =========================================================
def create_trend_matrix(dfs: dict[str, pd.DataFrame], threshold_func) -> pd.DataFrame:
    """
    Erstellt eine Trend-Matrix je Ticker mit p_up_daily / p_up_week / p_up_month.
    threshold_func(df) liefert den Schwellenwert (thr).
    """
    rows = []
    for tk, df in dfs.items():
        if df is None or df.empty:
            continue
        if "Close" not in df.columns:
            continue

        df = compute_returns(df)

        # --- Daily p_up ---
        try:
            p_up_daily = (df["Returns"].shift(-1) > 0).mean()
        except Exception:
            p_up_daily = np.nan

        # --- Weekly p_up ---
        try:
            df_week = df["Close"].resample("W-FRI").last().pct_change()
            p_up_week = (df_week.shift(-1) > 0).mean()
        except Exception:
            p_up_week = np.nan

        # --- Monthly p_up ---
        try:
            df_month = df["Close"].resample("M").last().pct_change()
            p_up_month = (df_month.shift(-1) > 0).mean()
        except Exception:
            p_up_month = np.nan

        # --- Volatility Ratio ---
        try:
            vr = (df["Returns"].rolling(21).var() / df["Returns"].rolling(5).var()).iloc[-1]
        except Exception:
            vr = np.nan

        # --- Threshold bestimmen ---
        try:
            thr = float(threshold_func(df))
        except Exception:
            thr = 0.5

        row = {
            "Ticker": tk,
            "p_up_daily": p_up_daily,
            "p_up_week": p_up_week,
            "p_up_month": p_up_month,
            "p_up_meta": np.nanmean(
                [v for v in (p_up_daily, p_up_week, p_up_month) if not pd.isna(v)]
            ),
            "VR": vr,
            "Threshold": thr,
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    trend_df = pd.DataFrame(rows).set_index("Ticker")
    trend_df["Signal"] = (
        trend_df["p_up_meta"] >= trend_df["Threshold"]
    ).map({True: "LONG", False: "NEUTRAL"})
    return trend_df


# =========================================================
# Default Threshold Helper
# =========================================================
def default_threshold_func(df: pd.DataFrame) -> float:
    """Einfacher Schwellenwert: mittlere Weekly-Trefferquote oder 0.5."""
    try:
        df_week = df["Close"].resample("W-FRI").last().pct_change()
        thr = (df_week.shift(-1) > 0).mean()
        if np.isfinite(thr):
            return float(thr)
    except Exception:
        pass
    return 0.5


# =========================================================
# ✅ Self-Test (nur bei direktem Aufruf, nicht beim Import)
# =========================================================
if __name__ == "__main__":
    import numpy as np
    import pandas as pd

    print("🚀 Starte Self-Test von markov_core_v1 …")

    dates = pd.date_range("2020-01-01", periods=400, freq="D")
    prices = pd.Series(
        np.cumprod(1 + np.random.normal(0.0005, 0.02, len(dates))),
        index=dates
    )
    df = pd.DataFrame({"Close": prices})

    # --- Preprocessing & Transition-Test ---
    df = preprocess_prices(df, "daily")
    trans, p_up = calc_transitions(df)
    print(f"✅ Transitions geladen: {len(trans)} Zustände, p_up mean={p_up.mean():.3f}")

    # --- Trend-Matrix-Test ---
    tm = create_trend_matrix({"SYN": df}, default_threshold_func)
    print("✅ Trend-Matrix erstellt:")
    print(tm.head())

    print("✅ Self-Test abgeschlossen.\n")


