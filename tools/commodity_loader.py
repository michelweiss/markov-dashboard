#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

# ============================================================
# 🔑 EOD API KEY LOADER (ENV → FILE FALLBACK, HARD FAIL)
# ============================================================

def load_eod_api_key():
    # 1) ENV (bevorzugt)
    key = os.getenv("EOD_API_KEY")
    if key and key.strip():
        return key.strip()

    # 2) Datei-Fallback (dein Standardpfad)
    path = Path("/Users/michelweiss/Documents/Python_for_Finance/api_token.txt")
    if path.exists():
        key = path.read_text().strip()
        if key:
            return key

    # 3) Hard-Fail, damit NIE wieder api_token=None auftritt
    raise RuntimeError("❌ EOD API Key nicht gefunden (ENV und api_token.txt leer/nicht vorhanden)")

API_KEY = load_eod_api_key()
print(f"✅ EOD API KEY GELADEN: {API_KEY[:6]}********")

# ============================================================
# EOD SERIES LOADER
# ============================================================

def load_eod_series(ticker, start="2018-01-01"):
    url = (
        f"https://eodhd.com/api/eod/{ticker}"
        f"?from={start}&fmt=json&api_token={API_KEY}"
    )

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    data = r.json()
    if not isinstance(data, list) or len(data) == 0:
        raise RuntimeError(f"❌ Keine Daten von EOD für {ticker}")

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df.rename(columns=str.capitalize, inplace=True)

    return df[["Open", "High", "Low", "Close"]]

# ============================================================
# BLOOMBERG COMMODITY SUB-INDICES
# ============================================================

def load_all_bcom_indices():
    BCOM = {
        "COCOA":       "BCOMCC.INDX",
        "CRUDE_OIL":   "BCOMCL.INDX",
        "CORN":        "BCOMCN.INDX",
        "COTTON":      "BCOMCT.INDX",
        "GOLD":        "BCOMGC.INDX",
        "COPPER":      "BCOMHG.INDX",
        "COFFEE":      "BCOMKC.INDX",
        "LIVE_CATTLE": "BCOMLC.INDX",
        "NATURAL_GAS": "BCOMNG.INDX",
        "PLATINUM":    "BCOMPL.INDX",
        "SILVER":      "BCOMSI.INDX",
        "SOYBEANS":    "BCOMSY.INDX",
        "WHEAT":       "BCOMWH.INDX",
    }

    series = {}
    for name, ticker in BCOM.items():
        print(f"📥 Lade {name} ({ticker}) …")
        series[name] = load_eod_series(ticker)

    return series

# ============================================================
# DOLLAR INDEX (DXY)
# ============================================================

def load_dxy():
    print("📥 Lade Dollar Index (DXY.INDX) …")
    return load_eod_series("DXY.INDX")

