#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import pandas as pd

def compute_commodity_regime(dxy_df, inflation_proxy=None):
    close = dxy_df["Close"]

    ema50  = close.ewm(span=50).mean()
    ema200 = close.ewm(span=200).mean()

    usd_bull = ema50.iloc[-1] > ema200.iloc[-1]

    regime = {
        "usd_trend": "BULL" if usd_bull else "BEAR",
        "risk_multiplier": 0.8 if usd_bull else 1.05
    }

    return regime

