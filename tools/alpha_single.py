#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# tools/alphalyzer/alpha_single.py

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from tools.prices_eodhd import tool_prices
from .alpha_core import (
    compute_alpha_series,
    alpha_zscore,
    alpha_persistence,
)

# ─────────────────────────────────────────────
# Standard-Config
# ─────────────────────────────────────────────
RF_TICKER = "US10Y.GBOND"
ALPHA_WINDOWS = (180, 252, 360)
Z_WIN = 360
PERSIST_WIN = 252


# ─────────────────────────────────────────────
# Alpha Drawdown
# ─────────────────────────────────────────────
def compute_alpha_drawdown(alpha_series: pd.Series) -> float:
    """
    Max-Drawdown auf der Alpha-Kurve:
    misst, wie weit das aktuelle Alpha vom historischen Alpha-Peak gefallen ist.
    Erwartet: alpha_series als Dezimal (0.35 = 35%).
    """
    s = alpha_series.dropna()
    if len(s) < 5:
        return np.nan

    peak = s.cummax()
    dd = s / peak - 1.0

    return float(dd.min())


# ─────────────────────────────────────────────
# ✅ KORRIGIERTER PRICE-LOADER (None-sicher, INDX-sicher)
# ─────────────────────────────────────────────
def _load_price_series(
    ticker: str,
    start: str = "2015-01-01",
    end: str | None = None
) -> pd.Series:
    """
    Holt Preise via tool_prices und gibt eine adjclose-Serie mit DatetimeIndex zurück.
    Robust gegen INDX / CC / Equities.
    """

    if end is None:
        end = datetime.utcnow().date().isoformat()

    # ✅ KORREKTER CALL (kein Dict mehr!)
    try:
        res = tool_prices(
            ticker=ticker,
            start=start,
            end=end,
            adjusted=True
        )
    except Exception as e:
        raise RuntimeError(f"tool_prices Crash bei {ticker}: {e}")

    # ✅ HARTER NONE-FALL
    if res is None:
        raise RuntimeError(
            f"EOD liefert None für {ticker}. "
            f"Sehr wahrscheinlich falsches Routing (INDX/CC/Equity)."
        )

    # ✅ Fehler sauber melden
    if isinstance(res, dict) and res.get("error"):
        raise RuntimeError(f"Fehler beim Laden von Preisen für {ticker}: {res.get('error')}")

    # ✅ DataFrame robuster Aufbau
    if isinstance(res, pd.DataFrame):
        df = res.copy()
    elif isinstance(res, dict):
        hist = res.get("history") or res.get("df") or res.get("data") or []
        df = pd.DataFrame(hist)
    else:
        raise RuntimeError(f"Unbekanntes Rückgabeformat für {ticker}: {type(res)}")

    if df.empty:
        raise RuntimeError(f"Keine Preisdaten für {ticker}")

    # --- Spalten vereinheitlichen ---
    df.columns = [str(c).lower() for c in df.columns]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
        df.set_index("date", inplace=True)

    # ✅ Priorität: adjusted
    for col in ("close_adj", "adjusted_close", "adjclose", "close"):
        if col in df.columns:
            close_col = col
            break
    else:
        raise RuntimeError(f"Keine Close-Spalte für {ticker} gefunden: {list(df.columns)}")

    s = pd.to_numeric(df[close_col], errors="coerce").dropna()
    s.name = ticker

    if len(s) < 50:
        raise RuntimeError(f"Zu wenig Daten für {ticker}: nur {len(s)} Werte")

    return s


# ─────────────────────────────────────────────
# Hauptfunktion: Alpha-Analyse
# ─────────────────────────────────────────────
def alphalyze_single(
    ticker: str,
    rf_ticker: str = RF_TICKER,
    start: str = "2018-01-01",
    windows=ALPHA_WINDOWS,
) -> dict:

    asset_close = _load_price_series(ticker, start=start)
    rf_close    = _load_price_series(rf_ticker, start=start)

    # ── PRICE REGIME (Momentum vs. Mean Reversion)
    ret = asset_close.pct_change().dropna()

    vr_short = ret.rolling(10).var()
    vr_long  = ret.rolling(60).var()
    vr = vr_long / vr_short

    y = asset_close.tail(60).values
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]

    vr_last = vr.iloc[-1] if len(vr.dropna()) else np.nan

    if np.isfinite(vr_last) and vr_last >= 1.05 and slope > 0:
        regime = "MOMENTUM"
    elif np.isfinite(vr_last) and vr_last <= 0.95:
        regime = "MEAN_REVERSION"
    else:
        regime = "NEUTRAL"

    alpha_df = compute_alpha_series(asset_close, rf_close, windows=windows)

    main_w = max(windows)
    alpha_main = alpha_df[f"alpha_ann_{main_w}"]

    z = alpha_zscore(alpha_main, window=Z_WIN)
    alpha_df["alpha_z_main"] = z

    pers = alpha_persistence(alpha_main, window=PERSIST_WIN)
    dd   = compute_alpha_drawdown(alpha_main)

    last_idx = alpha_df.dropna().index.max()
    snap = alpha_df.loc[last_idx]

    out = {
        "ticker": ticker,
        "rf": rf_ticker,
        "as_of": last_idx.isoformat(),
        "windows": list(windows),
        "alpha_last": {
            f"{w}": float(snap[f"alpha_ann_{w}"])
            for w in windows
            if not np.isnan(snap[f"alpha_ann_{w}"])
        },
        "alpha_z_main": float(snap["alpha_z_main"]) if np.isfinite(snap["alpha_z_main"]) else None,
        "alpha_persistence": pers,
        "alpha_max_dd": dd,
        "alpha_df": alpha_df,
        "regime": regime,
        "regime_vr": float(vr_last) if np.isfinite(vr_last) else None,
        "regime_slope": float(slope),
    }

    return out


# ─────────────────────────────────────────────
# Plot-Funktion
# ─────────────────────────────────────────────
import plotly.graph_objects as go
import plotly.subplots as sp

def make_alpha_figure(asset_close: pd.Series,
                      rf_close: pd.Series,
                      alpha_df: pd.DataFrame,
                      windows=ALPHA_WINDOWS):

    main_w = max(windows)
    z = alpha_df["alpha_z_main"]

    fig = sp.make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.4, 0.35, 0.25],
        vertical_spacing=0.03,
        subplot_titles=("Return Index vs. RF", "Annualisiertes Alpha", "Alpha Z-Score")
    )

    asset_ret = asset_close.pct_change().fillna(0.0)
    rf_yield  = rf_close / 100.0
    rf_ret    = rf_yield.pct_change().fillna(0.0)

    asset_idx = (1 + asset_ret).cumprod() * 100
    rf_idx    = (1 + rf_ret).cumprod() * 100

    fig.add_trace(go.Scatter(x=asset_idx.index, y=asset_idx.values,
                             name="Asset Return Index (100)", line=dict(width=1.5)),
                  row=1, col=1)

    fig.add_trace(go.Scatter(x=rf_idx.index, y=rf_idx.values,
                             name="RF Return Index (100)", line=dict(width=1, dash="dot")),
                  row=1, col=1)

    # Panel 2
    for w in windows:
        col = f"alpha_ann_{w}"
        if col in alpha_df.columns:
            fig.add_trace(go.Scatter(x=alpha_df.index, y=alpha_df[col],
                                     name=f"Alpha ann {w}d", line=dict(width=1)),
                          row=2, col=1)

    # Panel 3
    fig.add_trace(go.Scatter(x=z.index, y=z.values,
                             name="Alpha Z", line=dict(width=1.4, color="cyan")),
                  row=3, col=1)

    for lvl in (-2.0, -1.5, 0.0, 1.5, 2.0):
        fig.add_hline(y=lvl, line_width=0.8, line_dash="dot",
                      line_color="gray", row=3, col=1)

    fig.update_layout(
        height=800,
        showlegend=True,
        margin=dict(l=40, r=20, t=40, b=40),
        template="plotly_dark"
    )

    return fig

