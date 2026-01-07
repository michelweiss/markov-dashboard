#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# tools/alpha_universe.py

import pandas as pd
import numpy as np
from pathlib import Path

from .alpha_single import _load_price_series
from .alpha_core import compute_alpha_series, alpha_zscore, alpha_persistence

RF_TICKER = "US10Y.GBOND"
ALPHA_WINDOWS = (180, 252, 360)
Z_WIN = 360
PERSIST_WIN = 252


def load_universe_nasdaq100(path: str | Path) -> list[str]:
    p = Path(path).expanduser()
    text = p.read_text().strip().upper()

    # Komma- oder Zeilen-getrennt automatisch erkennen
    if "," in text:
        tickers = [t.strip() for t in text.split(",") if t.strip()]
    else:
        tickers = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.startswith("#")
        ]

    return tickers


def alphalyze_universe_nasdaq100(
    universe_file: str | Path,
    rf_ticker: str = RF_TICKER,
    start: str = "2018-01-01",
) -> pd.DataFrame:
    """
    Cross-Section Alpha-Analyse für das ganze Nasdaq100-Universum.
    Gibt ein DataFrame mit Kennzahlen je Ticker zurück.
    """
    tickers = load_universe_nasdaq100(universe_file)
    rf_close = _load_price_series(rf_ticker, start=start)

    rows = []

    for t in tickers:
        try:
            asset_close = _load_price_series(t, start=start)
            alpha_df = compute_alpha_series(asset_close, rf_close, windows=ALPHA_WINDOWS)

            main_w = max(ALPHA_WINDOWS)
            alpha_main = alpha_df[f"alpha_ann_{main_w}"]
            z = alpha_zscore(alpha_main, window=Z_WIN)
            pers = alpha_persistence(alpha_main, window=PERSIST_WIN)

            last = alpha_df.dropna().iloc[-1]

            rows.append({
                "Ticker": t,
                "alpha_ann_180": float(last.get("alpha_ann_180", np.nan)),
                "alpha_ann_252": float(last.get("alpha_ann_252", np.nan)),
                "alpha_ann_360": float(last.get("alpha_ann_360", np.nan)),
                "alpha_z_360": float(z.iloc[-1]) if np.isfinite(z.iloc[-1]) else np.nan,
                "alpha_persistence": float(pers),
            })
        except Exception:
            # TODO: Logging optional
            continue

    df = pd.DataFrame(rows)

    # ─────────────────────────────────────────────────────────
    # Kein Data → direkt zurück (verhindert KeyError)
    # ─────────────────────────────────────────────────────────
    if df.empty:
        return df

    # ─────────────────────────────────────────────────────────
    # Ranks + Percentiles
    # ─────────────────────────────────────────────────────────
    # Falls Spalten fehlen, werden sie vorher generiert, bevor sortiert wird.
    if "rank_alpha" not in df.columns:
        df["rank_alpha"] = df["alpha_ann_360"].rank(ascending=False, method="min")
    if "rank_persist" not in df.columns:
        df["rank_persist"] = df["alpha_persistence"].rank(ascending=False, method="min")

    # Percentile (für Anzeige Top-X%)
    if "alpha_percentile" not in df.columns:
        df["alpha_percentile"] = df["alpha_ann_360"].rank(pct=True, ascending=False)

    # ─────────────────────────────────────────────────────────
    # Regime-Klassifikation
    # ─────────────────────────────────────────────────────────
    def classify_row(row: pd.Series) -> str:
        alpha = row.get("alpha_ann_360", np.nan)
        pers  = row.get("alpha_persistence", np.nan)
        zval  = row.get("alpha_z_360", np.nan)

        if np.isfinite(alpha) and np.isfinite(pers):
            # Winner mit guter Historie
            if alpha > 0 and pers > 0.65:
                if np.isfinite(zval) and zval < -1.5:
                    return "REENTRY_LONG"
                return "ALPHA_WINNER"
            # Dauer-Verlierer
            if alpha < 0 and pers < 0.35:
                return "STRUCTURAL_LOSER"
        return "NEUTRAL"

    df["alpha_regime"] = df.apply(classify_row, axis=1)

    # ─────────────────────────────────────────────────────────
    # Sort nur, wenn die Spalten sicher existieren
    # ─────────────────────────────────────────────────────────
    sort_cols = []
    if "rank_alpha" in df.columns:
        sort_cols.append("rank_alpha")
    if "rank_persist" in df.columns:
        sort_cols.append("rank_persist")

    if sort_cols:
        df = df.sort_values(sort_cols, ascending=[True] * len(sort_cols))

    return df

