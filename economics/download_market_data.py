#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download SPX daily returns via EOD Historical Data
-------------------------------------------------
Used for macro reaction analysis
"""

import requests
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"
DATA_DIR.mkdir(exist_ok=True)

API_KEY = open("/users/michelweiss/documents/python_for_finance/api_token.txt").read().strip()

TICKER = "GSPC.INDX"
START  = "2000-01-01"

OUT_FILE = DATA_DIR / "spx_returns.csv"


def download_spx_eod():

    url = (
        f"https://eodhd.com/api/eod/{TICKER}"
        f"?from={START}"
        f"&period=d"
        f"&fmt=json"
        f"&api_token={API_KEY}"
    )

    r = requests.get(url)
    r.raise_for_status()

    data = r.json()
    df = pd.DataFrame(data)

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["ret_1d"] = df["adjusted_close"].pct_change()
    df = df.dropna()

    out = df[["date", "adjusted_close", "ret_1d"]]
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ SPX returns written via EOD: {OUT_FILE}")
    print(out.tail())


if __name__ == "__main__":
    download_spx_eod()

