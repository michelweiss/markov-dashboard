#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
from pathlib import Path

from tools.prices_eodhd import tool_prices

GLOBAL_START  = "2018-01-01"
FORWARD_START = "2025-01-01"
RF_TICKER     = "US10Y.GBOND"


# ─────────────────────────────────────────────
# Rebalance Kalender
# ─────────────────────────────────────────────
def compute_rebalance_dates(series: pd.Series, freq: str):
    if freq == "weekly":
        return series.resample("W-FRI").last().index
    elif freq == "monthly":
        return series.resample("M").last().index
    elif freq == "weekly_crypto":
        return series.resample("W-SUN").last().index
    else:
        raise ValueError("freq muss weekly | monthly | weekly_crypto sein")


# ─────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────
def compute_ytd_metrics(nav: pd.Series):

    nav = nav.dropna()
    ret = nav.pct_change().dropna()

    if len(ret) == 0:
        return dict(YTD=np.nan, CAGR=np.nan, Vol=np.nan, Sharpe=np.nan, MaxDD=np.nan)

    ytd = nav.iloc[-1] / nav.iloc[0] - 1
    cagr = (nav.iloc[-1]) ** (252 / len(ret)) - 1
    vol = ret.std() * np.sqrt(252)
    sharpe = cagr / vol if vol > 0 else np.nan

    dd = nav / nav.cummax() - 1
    max_dd = dd.min()

    return dict(YTD=ytd, CAGR=cagr, Vol=vol, Sharpe=sharpe, MaxDD=max_dd)


# ─────────────────────────────────────────────
# Turnover
# ─────────────────────────────────────────────
def compute_turnover(history_df: pd.DataFrame):

    prev = None
    changes = []

    for _, row in history_df.iterrows():
        cur = set(row["tickers"].split(","))

        if prev is not None:
            diff = len(cur.symmetric_difference(prev))
            changes.append(diff / len(cur))

        prev = cur

    return float(np.mean(changes)) if changes else 0.0


# ─────────────────────────────────────────────
# Train / Test
# ─────────────────────────────────────────────
def split_train_test(nav: pd.Series, split_year="2023-01-01"):

    nav = nav.dropna()
    train = nav[nav.index < split_year]
    test  = nav[nav.index >= split_year]

    return compute_ytd_metrics(train), compute_ytd_metrics(test)


# ─────────────────────────────────────────────
# ✅ Ticker Mapping
# ─────────────────────────────────────────────
def _map_ticker(tk: str, universe_name: str) -> str:
    t = tk.upper().strip()

    # bereits mit Suffix (FOREX, INDX, CC, US, …)
    if "." in t:
        return t

    uni = universe_name.lower()

    # Nasdaq-Universen: keine Suffixe
    if "nasdaq" in uni:
        return t

    # S&P-Universen: .US anhängen
    if "sp" in uni or "s&p" in uni:
        return f"{t}.US"

    # Fallback: nichts anhängen
    return t


# ─────────────────────────────────────────────
# ✅ HAUPT BACKTEST (ROBUST, OHNE alphalyze_single)
# ─────────────────────────────────────────────
def alphalyzer_backtest_standalone(
    universe_file: Path,
    freq: str = "weekly",
    top_n: int = 5
):

    universe_name = universe_file.name

    # Universe laden
    tickers = [
        t.strip().upper()
        for t in universe_file.read_text().replace("\n", "").split(",")
        if t.strip()
    ]

    # ─────────────────────────────
    # Preise laden
    # ─────────────────────────────
    px = {}
    failed_px = {}

    for tk in tickers:
        tk_mapped = _map_ticker(tk, universe_name)
        df = tool_prices(tk_mapped, start=GLOBAL_START)

        if df.empty or "close" not in df.columns:
            failed_px[tk] = tk_mapped
            continue

        px[tk] = df["close"]

    px = pd.DataFrame(px).dropna(how="all")

    if px.empty:
        raise RuntimeError(
            "❌ KEINE Preisdaten geladen!\n"
            f"Universe: {universe_name}\n"
            f"Fehlgeschlagene Ticker: {list(failed_px.keys())[:10]}"
        )

    # ─────────────────────────────
    # Risk Free
    # ─────────────────────────────
    rf_df = tool_prices(RF_TICKER, start=GLOBAL_START)
    if rf_df.empty or "close" not in rf_df.columns:
        raise RuntimeError(f"❌ Risk-Free Serie ({RF_TICKER}) konnte nicht geladen werden.")
    rf = rf_df["close"].pct_change().dropna()

    trade_dates = compute_rebalance_dates(px.iloc[:, 0], freq)

    # ─────────────────────────────
    # ✅ ALPHA BERECHNEN (excess return, dyn. Window)
    # ─────────────────────────────
    alpha_ts = {}

    for tk in px.columns:
        ret = px[tk].pct_change().dropna()
        df_joint = pd.concat([ret, rf], axis=1).dropna()

        if df_joint.empty:
            continue

        df_joint.columns = ["asset", "rf"]
        excess = df_joint["asset"] - df_joint["rf"]

        # dynamisches Fenster: min(252, 50 % der Historie), mind. 20 Tage
        win = min(252, max(20, int(len(excess) * 0.5)))
        alpha_roll = excess.rolling(window=win, min_periods=20).mean()

        alpha_ts[tk] = alpha_roll

    if not alpha_ts:
        raise RuntimeError(
            "❌ Keine Alpha-Serien berechnet – prüfe RF-Ticker und Preisserien."
        )

    nav = 1.0
    history = []

    # ─────────────────────────────
    # Rebalancing Loop
    # ─────────────────────────────
    for i in range(len(trade_dates) - 1):

        d0 = trade_dates[i]
        d1 = trade_dates[i + 1]

        # ✅ nur Forward-Phase handeln
        if d1 < pd.to_datetime(FORWARD_START):
            continue

        alpha_vals = {}

        for tk, s in alpha_ts.items():
            s_sub = s[s.index <= d0]
            if not s_sub.empty:
                alpha_vals[tk] = float(s_sub.iloc[-1])

        # Mindest-Signalbreite (sonst Skip)
        if len(alpha_vals) < max(3, top_n):
            continue

        alpha_snap = pd.Series(alpha_vals).dropna()
        if alpha_snap.empty:
            continue

        top = alpha_snap.sort_values(ascending=False).head(top_n).index.tolist()

        try:
            p0 = px.loc[d0, top]
            p1 = px.loc[d1, top]
        except KeyError:
            # falls einzelne Preise fehlen → Rebalance überspringen
            continue

        ret = (p1 / p0 - 1).mean()
        nav *= (1 + ret)

        history.append({
            "date": d1,
            "tickers": ",".join(top),
            "ret": float(ret),
            "nav": float(nav)
        })

    if not history:
        raise RuntimeError("❌ Kein einziges Rebalancing möglich – Alpha oder Preise nie gleichzeitig gültig.")

    nav_series = pd.Series(
        [h["nav"] for h in history],
        index=pd.to_datetime([h["date"] for h in history])
    )

    # ✅ Nur Forward-Phase für KPIs (ab FORWARD_START)
    nav_forward = nav_series[nav_series.index >= FORWARD_START]
    metrics_all = compute_ytd_metrics(nav_forward)

    return nav_series, pd.DataFrame(history), metrics_all

