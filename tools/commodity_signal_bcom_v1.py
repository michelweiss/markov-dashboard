#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

# -----------------------------------------------------------
# Bloomberg Commodity Index Signal Engine (v1)
# -----------------------------------------------------------

def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def atr(df, n=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean()

# -----------------------------------------------------------
# MAIN SIGNAL FUNCTION
# -----------------------------------------------------------

def compute_bcom_commodity_signal(
    ticker: str,
    price_df: pd.DataFrame,
    dxy_df: pd.DataFrame | None = None
):
    """
    price_df: Bloomberg Commodity Index OHLC
    dxy_df  : US Dollar Index (optional)
    """

    df = price_df.copy().dropna().tail(300)

    if len(df) < 200:
        return {
            "asset": ticker,
            "signal": "FLAT",
            "confidence": 0.20,
            "engine": "commodity_bcom_v1",
            "reason": "insufficient_history"
        }

    close = df["Close"]

    ema50  = ema(close, 50)
    ema200 = ema(close, 200)

    # --- Trend ---
    if ema50.iloc[-1] > ema200.iloc[-1]:
        trend = 1
    elif ema50.iloc[-1] < ema200.iloc[-1]:
        trend = -1
    else:
        trend = 0

    # --- Volatility Regime (Indizes sind ruhiger als Futures) ---
    atr14 = atr(df, 14)
    atr_pct = atr14.iloc[-1] / close.iloc[-1]
    high_vol = atr_pct > 0.032      # niedriger als Futures-Threshold

    # --- USD Filter (stärkerer Effekt auf Indizes) ---
    usd_penalty = 0.0
    if dxy_df is not None and len(dxy_df) > 200:
        dxy_close = dxy_df["Close"].dropna()
        dxy_50 = ema(dxy_close, 50)
        dxy_200 = ema(dxy_close, 200)

        if dxy_50.iloc[-1] > dxy_200.iloc[-1]:
            usd_penalty = 0.30   # stärker als Futures-Version

    # --- Signal Mapping ---
    if trend == 1:
        signal = "LONG"
        base_conf = 0.75
    elif trend == -1:
        signal = "SHORT"
        base_conf = 0.75
    else:
        signal = "FLAT"
        base_conf = 0.35

    # --- Confidence Modulation ---
    conf = base_conf

    if high_vol:
        conf -= 0.20

    conf -= usd_penalty

    conf = float(np.clip(conf, 0.20, 0.95))

    return {
        "asset": ticker,
        "signal": signal,
        "confidence": round(conf, 4),
        "engine": "commodity_bcom_v1",
        "features": {
            "trend": trend,
            "atr_pct": round(float(atr_pct), 4),
            "high_vol": bool(high_vol),
            "usd_penalty": usd_penalty
        }
    }

