#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# alpha_core.py
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def rolling_annualized_return(ret: pd.Series, window: int) -> pd.Series:
    """
    Rolling annualisierte Rendite über 'window' Handelstage (geometrisch).
    ret: tägliche Returns (z.B. pct_change)
    """
    def _ann(x: pd.Series) -> float:
        x = x.values
        x = x[np.isfinite(x)]
        if len(x) == 0:
            return np.nan
        gross = np.prod(1.0 + x)
        if gross <= 0:
            return np.nan
        return gross ** (TRADING_DAYS / len(x)) - 1.0

    return ret.rolling(window, min_periods=window).apply(_ann, raw=False)


def compute_alpha_series(asset_close: pd.Series,
                         rf_close: pd.Series,
                         windows=(180, 252, 360)) -> pd.DataFrame:
    """
    Berechnet annualisiertes Alpha für mehrere Fenster.

    WICHTIG:
    - asset_close  = bereinigter Preis (close_adj)
    - rf_close     = Bond-YIELD in Prozent (z. B. 4.25)
    - Alpha wird auf DAILY RETURN BASIS berechnet:
        r_asset - r_rf

    Index: gemeinsame Handelstage (DatetimeIndex)
    Spalten:
      ['asset', 'rf', 'ret_asset', 'ret_rf',
       'alpha_ann_180', 'alpha_ann_252', ...]
    """

    # --- Gemeinsame Zeitbasis ---
    df = pd.concat(
        [asset_close.rename("asset"),
         rf_close.rename("rf_yield_pct")],
        axis=1
    ).dropna()

    # --- Asset Return ---
    df["ret_asset"] = df["asset"].pct_change()

    # --- RF: Yield (%) → Dezimal → Return ---
    df["rf_yield"] = df["rf_yield_pct"] / 100.0
    df["ret_rf"]   = df["rf_yield"].pct_change()

    # --- Rolling Alpha (annualisiert) ---
    for w in windows:
        a_ann  = rolling_annualized_return(df["ret_asset"], w)
        rf_ann = rolling_annualized_return(df["ret_rf"], w)
        df[f"alpha_ann_{w}"] = a_ann - rf_ann

    return df


def alpha_zscore(alpha: pd.Series, window: int = 360) -> pd.Series:
    mu  = alpha.rolling(window, min_periods=window).mean()
    std = alpha.rolling(window, min_periods=window).std()

    std = std.replace(0, np.nan)
    z   = (alpha - mu) / std

    return z.clip(-5, 5)



def alpha_persistence(alpha: pd.Series, window: int = 252) -> float:
    """
    Anteil Tage mit Alpha > 0 im Fenster (z.B. 1 Jahr ≈ 252 Handelstage).
    """
    tail = alpha.tail(window).dropna()
    if len(tail) == 0:
        return np.nan
    return float((tail > 0).mean())


def alpha_max_drawdown(alpha: pd.Series) -> float:
    """
    Maximaler Drawdown der kumulierten Alpha-Kurve.
    alpha: Tages-Alpha ODER annualisiertes Alpha (dann interpretativ).
    """
    cum = alpha.cumsum().dropna()
    if cum.empty:
        return np.nan
    roll_max = cum.cummax()
    dd = cum - roll_max
    return float(dd.min())  # negativer Wert

