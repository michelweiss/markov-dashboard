#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download DXY daily returns via EOD
----------------------------------
Used for CPI reaction analysis
"""

import requests
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"
DATA_DIR.mkdir(exist_ok=True)

API_KEY = open("/users/michelweiss/documents/python_for_finance/api_token.txt").read().strip()

TICKER = "DXY.INDX"
START  = "2000-01-01"
OUT_FILE = DATA_DIR / "dxy_returns.csv"


def download_dxy():

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
        raise RuntimeError("Empty DXY data from EOD")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # prefer adjusted_close if present
    px_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
    df["price"] = df[px_col].astype(float)
    df["ret_1d"] = df["price"].pct_change()
    df = df.dropna()

    out = df[["date", "price", "ret_1d"]]
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ DXY returns written: {OUT_FILE}")
    print(out.tail())


if __name__ == "__main__":
    download_dxy()

