#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
#  MARKOV CORE v4 · Rolling Probability Engine (2026-01)
#  - Rolling windows statt kalenderfixem Resampling (W-FRI / M)
#  - Ideal für Financial-Kontext: "Regime jetzt" (d/w/m rolling)
#  - Markov-Transitions bleiben identisch (3-State auf y_bin)
#
#  Rolling-Definition (Trading Days):
#    daily   : window=1   (t-2 -> t-1 wird im Caller via slicing gemacht ODER window=1+1)
#    weekly  : window=5
#    monthly : window=21
#
#  Hinweis:
#  - v3 bleibt unangetastet für Trading/Screener (kalenderfix).
#  - v4 ist bewusst "rolling-first".
# ------------------------------------------------------------------

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from typing import Dict, Tuple, Optional, Iterable
import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# Public constants
# ------------------------------------------------------------------
AHEAD: int = 1
START: Optional[str] = None  # optionaler Datumsfilter als ISO-String (z.B. "2022-01-01")

WARMUP_BARS = {
    "daily":   756,    # ~3 Jahre
    "weekly":  756,    # ~3 Jahre
    "monthly": 1260,   # ~5 Jahre
}

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

    if "Close" not in df.columns:
        for c in list(df.columns):
            if c in col_map:
                df = df.rename(columns={c: "Close"})
        if "Close" not in df.columns:
            return pd.DataFrame()

    df = df[["Close"]].copy()

    # Index zu Datetime, sortiert, ohne Duplikate
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()].sort_index()
    df = df[~df.index.duplicated(keep="last")]

    return df


# ------------------------------------------------------------------
# Preprocessing (v4 = kein Resample, nur Clean + optional START-Filter)
# ------------------------------------------------------------------
def preprocess_prices(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    v4: Keine kalenderfixe Aggregation.
    Nur Normalisierung, Sortierung, DropNA und optional START-Filter.
    Rolling-Windows werden im Caller via tail(window+K) gemacht.
    """
    df = _normalize_df(df_raw)
    if df.empty:
        return df

    # Optionaler Filter via START (global)
    try:
        if START:
            df = df.loc[pd.to_datetime(START):]
    except Exception:
        pass

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
    out["Returns"] = np.log(out["Close"] / out["Close"].shift(1))
    out = out.dropna(subset=["Close", "Returns"])
    out["y_bin"] = (out["Returns"] > 0).astype(int)
    return out

def compute_returns_horizon(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """
    Log-Returns über einen festen Trading-Day-Horizont (rolling).
    horizon = 1 / 5 / 21
    """
    if df is None or df.empty or horizon < 1:
        return pd.DataFrame()

    out = df.copy()
    out["Returns"] = np.log(out["Close"] / out["Close"].shift(horizon))
    out = out.dropna(subset=["Close", "Returns"])
    out["y_bin"] = (out["Returns"] > 0).astype(int)
    return out

def calc_transitions_horizon(
    df: pd.DataFrame,
    horizon: int,
    ahead: int = AHEAD,
    shrink_k: int = 15,
    return_series: bool = True,
):
    """
    Markov-Transitions auf Horizon-Returns mit Bayes-Shrinkage.
    """
    base = compute_returns_horizon(df, horizon=horizon)
    if base.empty or len(base) < ahead + 3:
        return {}, pd.Series(dtype=float)

    y = base["y_bin"].to_numpy()
    idx = np.arange(2, len(base) - ahead)

    states = np.vstack([y[idx - 2], y[idx - 1], y[idx]]).T
    states_tuples = [tuple(row) for row in states]
    y_next = y[idx + ahead]

    trans = {}

    st_arr = np.array(states_tuples, dtype=int)
    codes = (st_arr[:, 0] << 2) + (st_arr[:, 1] << 1) + st_arr[:, 2]

    for code in range(8):
        mask = codes == code
        if not np.any(mask):
            continue

        n = int(mask.sum())
        wins = int(np.sum(y_next[mask] == 1))

        # Empirical Bayes Shrinkage → verhindert 0 / 1
        p_up = (wins + 0.5 * shrink_k) / (n + shrink_k)

        a = (code >> 2) & 1
        b = (code >> 1) & 1
        c = code & 1
        trans[(a, b, c)] = {"0": 1.0 - p_up, "1": p_up, "n": n}

    if not return_series:
        return trans, pd.Series(dtype=float)

    p_up_vals = [trans.get(s, {"1": np.nan})["1"] for s in states_tuples]
    p_up_series = pd.Series(p_up_vals, index=base.index[idx], name="p_up")

    return trans, p_up_series


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

    v4: Identisch zu v3, nur ohne freq/resample-Logik.
    """
    base = compute_returns(df)
    if base.empty or len(base) < ahead + 3:
        return {}, pd.Series(dtype=float)

    y = base["y_bin"].to_numpy()
    idx = np.arange(2, len(base) - ahead)  # (t-2,t-1,t) existiert & t+ahead existiert

    states = np.vstack([y[idx - 2], y[idx - 1], y[idx]]).T
    states_tuples = [tuple(row) for row in states]
    y_next = y[idx + ahead]

    trans: Dict[Tuple[int, int, int], Dict[str, float]] = {}

    if len(states_tuples) > 0:
        st_arr = np.array(states_tuples, dtype=int)
        codes = (st_arr[:, 0] << 2) + (st_arr[:, 1] << 1) + st_arr[:, 2]  # 0..7

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
        return trans, pd.Series(dtype=float)

    p_up_vals = [trans.get(s, {"1": np.nan})["1"] for s in states_tuples]
    p_up_series = pd.Series(p_up_vals, index=base.index[idx], name="p_up")

    return trans, p_up_series


# ------------------------------------------------------------------
# Rolling utilities (v4 Kern)
# ------------------------------------------------------------------
def rolling_slice(df_raw: pd.DataFrame, window: int, ahead: int = AHEAD) -> pd.DataFrame:
    """
    Liefert einen Preis-DF, der groß genug ist, um den letzten Markov-State
    und y_next zu berechnen.
    Minimal erforderlich: window + (state_len=3) + ahead
    Plus 1 extra, weil compute_returns shift(1) braucht.
    """
    df = preprocess_prices(df_raw)
    if df.empty:
        return df

    need = int(window) + 3 + int(ahead) + 1
    if len(df) < need:
        return df.tail(len(df))

    return df.tail(need)


def rolling_p_up_last(
    df_raw: pd.DataFrame,
    freq: str,
    horizon: int,
    ahead: int = AHEAD,
    shrink_k: int = 15,
    return_n: bool = False,
):
    """
    Stabiler Rolling p_up mit frequenzabhängigem Warm-up.

    Rückgabe:
      - float p_up               (default)
      - (p_up, n_samples)        wenn return_n=True
    """
    df = preprocess_prices(df_raw)
    if df is None or df.empty:
        return (float("nan"), 0) if return_n else float("nan")

    # Warm-up je Frequenz
    warmup = WARMUP_BARS.get(freq, 756)
    base = df.tail(int(warmup))

    trans, p_ser = calc_transitions_horizon(
        base,
        horizon=int(horizon),
        ahead=ahead,
        shrink_k=shrink_k,
        return_series=True,
    )

    if p_ser is None or p_ser.empty:
        return (float("nan"), 0) if return_n else float("nan")

    p_last = float(p_ser.iloc[-1])

    if not return_n:
        return p_last

    # ── n_samples des letzten beobachteten States
    # State = letzte 3 y_bin-Werte auf Horizon-Basis
    base_ret = compute_returns_horizon(base, horizon=int(horizon))
    if base_ret is None or len(base_ret) < 3:
        return p_last, 0

    y = base_ret["y_bin"].to_numpy()
    state = tuple(y[-3:])
    n_samples = int(trans.get(state, {}).get("n", 0))

    return p_last, n_samples




def rolling_p_up_mean(df_raw: pd.DataFrame, window: int, ahead: int = AHEAD) -> float:
    """
    Optional: mittleres p_up im Rolling-Fenster (falls du es brauchst).
    Standard für Financial ist usually rolling_p_up_last.
    """
    df = rolling_slice(df_raw, window=window, ahead=ahead)
    if df is None or df.empty:
        return float("nan")
    _, p_ser = calc_transitions(df, ahead=ahead, return_series=True)
    return float(p_ser.mean()) if p_ser is not None and not p_ser.empty else float("nan")


# ------------------------------------------------------------------
# Default-Threshold (optional – bleibt wie v3)
# ------------------------------------------------------------------
def default_threshold_func(df: pd.DataFrame) -> float:
    """
    Robuster Fallback-Optimizer: grid über 0.30..0.70 und wählt den besten CumRet
    auf Basis der p_up-Serie.
    """
    try:
        _, p_ser = calc_transitions(df)
        if p_ser.empty:
            return 0.55
        rets = compute_returns(df)["Returns"].reindex(p_ser.index).shift(-AHEAD).dropna()
        p = p_ser.reindex(rets.index).fillna(0.5).to_numpy()
        r = rets.to_numpy()
        best_t, best_perf = 0.55, -np.inf
        for t in np.linspace(0.30, 0.70, 21):
            sign = np.where(p >= t, 1.0, -1.0)
            perf = np.sum(np.log1p(sign * r))
            if perf > best_perf:
                best_perf, best_t = perf, t
        return float(best_t)
    except Exception:
        return 0.55


# ------------------------------------------------------------------
# Rolling Trend Matrix (für Financial)
# ------------------------------------------------------------------
def create_rolling_trend_matrix(
    dfs: Dict[str, pd.DataFrame],
    windows: Optional[Dict[str, int]] = None,
    use_last: bool = True,
    threshold_func=default_threshold_func,
    threshold_window: int = 63,  # ~3 Monate Trading Days als Basis
) -> pd.DataFrame:
    """
    Baut eine Rolling Trend-Matrix (Financial-Style) über mehrere Ticker/Indizes.

    Standard windows:
      daily=1, weekly=5, monthly=21 (Trading Days)

    use_last:
      True  -> rolling_p_up_last (empfohlen für "Regime jetzt")
      False -> rolling_p_up_mean

    Threshold:
      optional, wird auf einem Rolling-Slice (threshold_window) geschätzt.
      Kannst du im Financial-UI auch weglassen.
    """
    if windows is None:
        windows = {"daily": 1, "weekly": 5, "monthly": 21}

    rows = []
    for tk, raw in (dfs or {}).items():
        try:
            fn = rolling_p_up_last if use_last else rolling_p_up_mean

            p_d = fn(raw, windows["daily"])
            p_w = fn(raw, windows["weekly"])
            p_m = fn(raw, windows["monthly"])

            # Threshold auf recent history (rolling) – optional
            df_thr = preprocess_prices(raw).tail(int(threshold_window) + 3 + AHEAD + 1)
            thr = float(threshold_func(df_thr)) if df_thr is not None and not df_thr.empty else 0.55

            rows.append({
                "Ticker": tk,
                "p_up_daily": p_d,
                "p_up_week": p_w,
                "p_up_month": p_m,
                "Threshold": thr,
            })

        except Exception:
            rows.append({
                "Ticker": tk,
                "p_up_daily": np.nan,
                "p_up_week": np.nan,
                "p_up_month": np.nan,
                "Threshold": np.nan,
            })

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows).set_index("Ticker")
    for c in ["p_up_daily", "p_up_week", "p_up_month", "Threshold"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


# ------------------------------------------------------------------
# Small self-test
# ------------------------------------------------------------------
if __name__ == "__main__":
    rng = pd.date_range("2024-01-01", periods=300, freq="B")
    rnd = pd.Series(np.random.randn(len(rng)) * 0.01, index=rng)
    px = 100 * np.exp(rnd.cumsum())
    df = pd.DataFrame({"Close": px}, index=rng)

    print("rolling_p_up_last daily(1):", rolling_p_up_last(df, 1))
    print("rolling_p_up_last weekly(5):", rolling_p_up_last(df, 5))
    print("rolling_p_up_last monthly(21):", rolling_p_up_last(df, 21))

    tm = create_rolling_trend_matrix({"DEMO": df})
    print("\nRolling TrendMatrix:\n", tm)

