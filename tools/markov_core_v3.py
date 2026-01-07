#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
#  MARKOV CORE v3 · Unified Probability Engine (2025-10)
#  - Stabile, einheitliche Rückgaben (dict, p_up_series)
#  - Sauberes Resampling (daily/weekly/monthly)
#  - Kompatibel mit Screenern, Tradern & Fusion
# ------------------------------------------------------------------

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Iterable, Optional
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ------------------------------------------------------------------
# Public constants (werden in deinen Skripten oft importiert)
# ------------------------------------------------------------------
AHEAD: int = 1         # wie viele Schritte in die Zukunft blicken
START: Optional[str] = None  # optionales Datumsfilter als ISO-String (z. B. "2022-01-01")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _normalize_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Sorgt dafür, dass ein DataFrame mindestens eine 'Close'-Spalte hat und
    einen sauberen, sortierten DatetimeIndex."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()

    # Spaltennamen grob normalisieren (case/alias)
    col_map = {
        "close": "Close", "Close": "Close", "adj_close": "Close", "Adj Close": "Close",
        "c": "Close", "price": "Close"
    }
    # vorhandene, brauchbare Spalte finden
    if "Close" not in df.columns:
        for c in df.columns:
            if c in col_map:
                df = df.rename(columns={c: "Close"})
        if "Close" not in df.columns:
            # kein Close auffindbar
            return pd.DataFrame()

    # Nur Close verwenden – Core ist bewusst schlank
    df = df[["Close"]].copy()

    # Index zu Datetime, sortiert, ohne Duplikate
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()].sort_index()
    df = df[~df.index.duplicated(keep="last")]

    return df


# ------------------------------------------------------------------
# Preprocessing
# ------------------------------------------------------------------
def preprocess_prices(df_raw: pd.DataFrame, freq: str = "daily", res: Optional[str] = None) -> pd.DataFrame:
    """
    Resampelt und säubert einen Preis-DataFrame auf die gewünschte Frequenz.
    Unterstützt: 'daily' (keine Resample), 'weekly' (W-FRI), 'monthly' (M).
    """
    df = _normalize_df(df_raw)
    if df.empty:
        return df

    f = (freq or "daily").lower()

    if f == "weekly":
        rule = "W-FRI"
        if res in ("SUN", "Sunday", "W-SUN"):
            rule = "W-SUN"
        df = df.resample(rule).last()
    elif f == "monthly":
        df = df.resample("M").last()
    # else: daily → keine Änderung

    return df.dropna()


# ------------------------------------------------------------------
# Returns & Binarisierung
# ------------------------------------------------------------------
def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fügt Spalten 'Returns' (log-returns) und 'y_bin' (1 wenn Return>0 sonst 0) hinzu.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    # Log-Return (numerisch stabil, additiv)
    out["Returns"] = np.log(out["Close"] / out["Close"].shift(1))
    out = out.dropna(subset=["Close", "Returns"])
    out["y_bin"] = (out["Returns"] > 0).astype(int)
    return out


# ------------------------------------------------------------------
# Markov-Transitions (3-State) → (dict, p_up_series)
# ------------------------------------------------------------------
def calc_transitions(
    df: pd.DataFrame,
    ahead: int = AHEAD,
    return_series: bool = True
) -> Tuple[Dict[Tuple[int, int, int], Dict[str, float]], pd.Series]:
    """
    Schätzt 3-State-Markov-Übergangswahrscheinlichkeiten basierend auf y_bin.
    Rückgabe:
      - transition_dict: {(a,b,c): {"0": p_down, "1": p_up}, ...}
      - p_up_series: Serie (Index aligniert), die je Zeile p_up(state_t) trägt
    """
    base = compute_returns(df)
    if base.empty or len(base) < ahead + 3:
        return {}, pd.Series(dtype=float)

    # Optionaler Filter via START (global)
    try:
        if START:
            base = base.loc[pd.to_datetime(START):]
    except Exception:
        pass

    y = base["y_bin"].to_numpy()
    # gültige "heutige" Indizes, für die (t-2,t-1,t) existiert UND t+ahead existiert
    idx = np.arange(2, len(base) - ahead)

    # Zustände (a,b,c) als Tripel
    states = np.vstack([y[idx - 2], y[idx - 1], y[idx]]).T  # shape (N, 3)
    states_tuples = [tuple(row) for row in states]

    # Zielvariable (nächster Binär-Return)
    y_next = y[idx + ahead]

    # Transitions schätzen: für jeden Zustand Anteil der "1" im y_next
    trans: Dict[Tuple[int, int, int], Dict[str, float]] = {}
    if len(states_tuples) > 0:
        # Map von Zustand → Liste der y_next
        # (vektorisiert via grouping)
        st_arr = np.array(states_tuples, dtype=int)
        # kodieren (a,b,c) → 4a + 2b + c in [0..7]
        codes = (st_arr[:, 0] << 2) + (st_arr[:, 1] << 1) + st_arr[:, 2]
        for code in range(8):
            mask = codes == code
            if not np.any(mask):
                continue
            p_up = float(np.mean(y_next[mask] == 1))
            a = (code >> 2) & 1
            b = (code >> 1) & 1
            c = code & 1
            trans[(a, b, c)] = {"0": 1.0 - p_up, "1": p_up}

    if not return_series:
        # Für Backward-Kompatibilität – wird bei dir normalerweise True sein
        return trans, pd.Series(dtype=float)

    # p_up Serie je beobachteter Zeile
    p_up_vals = [trans.get(s, {"1": np.nan})["1"] for s in states_tuples]
    p_up_series = pd.Series(p_up_vals, index=base.index[idx], name="p_up")

    return trans, p_up_series


# ------------------------------------------------------------------
# Default-Threshold (Fallback, deterministic-ish)
# ------------------------------------------------------------------
def default_threshold_func(df: pd.DataFrame) -> float:
    """
    Ein kleiner, robuster Fallback-Optimizer: grid über 0.30..0.70 und
    wählt den besten CumRet auf Basis der p_up-Serie.
    """
    try:
        _, p_ser = calc_transitions(df)
        if p_ser.empty:
            return 0.55
        rets = compute_returns(df)["Returns"].reindex(p_ser.index).shift(-AHEAD).dropna()
        # Align
        p = p_ser.reindex(rets.index).fillna(0.5).to_numpy()
        r = rets.to_numpy()
        best_t, best_perf = 0.55, -np.inf
        for t in np.linspace(0.30, 0.70, 21):
            sign = np.where(p >= t, 1.0, -1.0)
            perf = np.sum(np.log1p(sign * r))  # log-wealth
            if perf > best_perf:
                best_perf, best_t = perf, t
        return float(best_t)
    except Exception:
        return 0.55


# ------------------------------------------------------------------
# Trend-Matrix (Mehr-Ticker, Multi-Frequency)
# ------------------------------------------------------------------
def _mean_p_up(df: pd.DataFrame) -> float:
    """Hilfsfunktion: mittleres p_up einer Serie für ein DF (freq egal)."""
    _, p = calc_transitions(df)
    return float(p.mean()) if not p.empty else np.nan


def create_trend_matrix(
    dfs: Dict[str, pd.DataFrame],
    threshold_func = default_threshold_func,
    include_regime: bool = False,
) -> pd.DataFrame:
    """
    Baut eine kompakte Trend-Matrix über mehrere Ticker.
    Spalten:
      - p_up_daily, p_up_week, p_up_month
      - Threshold (pro Ticker)
      - optional: VR (Regime-Proxy – hier einfache Varianzratio)
    """
    rows = []
    for tk, raw in (dfs or {}).items():
        try:
            d_daily   = preprocess_prices(raw, "daily")
            d_weekly  = preprocess_prices(raw, "weekly")
            d_monthly = preprocess_prices(raw, "monthly")

            p_d = _mean_p_up(d_daily)   if not d_daily.empty   else np.nan
            p_w = _mean_p_up(d_weekly)  if not d_weekly.empty  else np.nan
            p_m = _mean_p_up(d_monthly) if not d_monthly.empty else np.nan

            # Threshold auf Basis der "führenden" Frequenz bestimmen (weekly bevorzugt)
            df_thr_base = d_weekly if not d_weekly.empty else (d_daily if not d_daily.empty else d_monthly)
            thr = float(threshold_func(df_thr_base)) if df_thr_base is not None and not df_thr_base.empty else 0.55

            row = {
                "Ticker": tk,
                "p_up_daily":  p_d,
                "p_up_week":   p_w,
                "p_up_month":  p_m,
                "Threshold":   thr,
            }

            if include_regime:
                # Sehr einfacher VR-Proxy: Varianz der Wochenreturns / Monatsreturns
                try:
                    wr = compute_returns(d_weekly)["Returns"]
                    mr = compute_returns(d_monthly)["Returns"]
                    vr = (wr.var() / mr.var()) if wr.size > 5 and mr.size > 3 and mr.var() else np.nan
                except Exception:
                    vr = np.nan
                row["VR"] = vr

            rows.append(row)

        except Exception:
            rows.append({
                "Ticker": tk,
                "p_up_daily": np.nan, "p_up_week": np.nan, "p_up_month": np.nan,
                "Threshold": np.nan, **({"VR": np.nan} if include_regime else {})
            })

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out = out.set_index("Ticker")
    # numerische Spalten konvertieren
    for c in ["p_up_daily", "p_up_week", "p_up_month", "Threshold", "VR"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


# ------------------------------------------------------------------
# Small self-test (run directly)
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Mini-Demo mit zufälligem Walk
    rng = pd.date_range("2024-01-01", periods=300, freq="B")
    rnd = pd.Series(np.random.randn(len(rng))*0.01, index=rng)
    px  = 100 * np.exp(rnd.cumsum())
    df  = pd.DataFrame({"Close": px}, index=rng)

    T, p = calc_transitions(df)
    print("Transitions (keys):", list(T.keys())[:3], "…")
    print("p_up_series last 5:\n", p.tail())

    tm = create_trend_matrix({"DEMO": df}, include_regime=True)
    print("\nTrendMatrix:\n", tm)

