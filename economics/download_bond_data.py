#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download US 10Y Treasury yield via EOD
--------------------------------------
Used for CPI reaction analysis
"""

import requests
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"
DATA_DIR.mkdir(exist_ok=True)

API_KEY = open("/users/michelweiss/documents/python_for_finance/api_token.txt").read().strip()

TICKER = "US10Y.GBOND"
START  = "2000-01-01"
OUT_FILE = DATA_DIR / "us10y_yield.csv"


def download_us10y():

    url = f"https://eodhd.com/api/eod/{TICKER}"
    params = {
        "from": START,
        "period": "d",
        "fmt": "json",
        "api_token": API_KEY,
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    df = pd.DataFrame(r.json())
    if df.empty:
        raise RuntimeError("Empty US10Y data from EOD")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # EOD GBOND usually has 'close' = yield level
    px_col = "close" if "close" in df.columns else "adjusted_close"
    df["yield"] = df[px_col].astype(float)

    # daily change in basis points
    df["d_yield_bp"] = df["yield"].diff() * 100.0
    df = df.dropna()

    out = df[["date", "yield", "d_yield_bp"]]
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ US10Y yield written: {OUT_FILE}")
    print(out.tail())


if __name__ == "__main__":
    download_us10y()

