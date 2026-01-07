#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# Markov/tools/prices_eodhd.py

import os
import datetime as dt
import pandas as pd
import httpx
from pathlib import Path

# ─────────────────────────────────────────────
# ✅ API CONFIG
# ─────────────────────────────────────────────
API_KEY_PATH = os.path.expanduser("~/documents/python_for_finance/api_token.txt")
BASE_URL = "https://eodhistoricaldata.com/api"


def _load_key() -> str:
    with open(API_KEY_PATH, "r") as f:
        return f.read().strip()


# ─────────────────────────────────────────────
# ✅ ASSET TYPE DETECTION
# ─────────────────────────────────────────────
def detect_asset_type(ticker: str) -> str:

    t = ticker.upper().strip()

    if t.endswith(".FOREX"):
        return "forex"

    if t.endswith(".INDX"):
        return "index"

    if t.endswith(".CC"):
        return "crypto"

    if "-" in t and "." not in t:
        return "crypto"

    return "stock"


# ─────────────────────────────────────────────
# ✅ LOW LEVEL EOD FETCH
# ─────────────────────────────────────────────
def fetch_history(
    ticker: str,
    start: str = "2020-01-01",
    end: str | None = None,
    adjusted: bool = True
) -> pd.DataFrame:

    token = _load_key()

    if end is None:
        end = dt.date.today().isoformat()

    url = (
        f"{BASE_URL}/eod/{ticker}"
        f"?api_token={token}"
        f"&from={start}"
        f"&to={end}"
        f"&period=d"
        f"&adjusted={'true' if adjusted else 'false'}"
        f"&fmt=json"
    )

    with httpx.Client(timeout=30) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()

    df = pd.DataFrame(data)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df.set_index("date", inplace=True)
    df.rename(columns=lambda c: c.strip().lower(), inplace=True)

    # ✅ adjusted erzwingen
    if "adjusted_close" in df.columns:
        df["close"] = df["adjusted_close"]

    return df


# ─────────────────────────────────────────────
# ✅ METRICS (OPTIONAL)
# ─────────────────────────────────────────────
def simple_metrics(df: pd.DataFrame) -> dict:

    if df.empty:
        return {"n": 0}

    px = df["close"]

    ret = px.pct_change()
    vol = ret.std() * (252 ** 0.5)
    cagr = (px.iloc[-1] / px.iloc[0]) ** (252 / len(px)) - 1
    dd = (px / px.cummax() - 1).min()

    return {
        "n": len(df),
        "vol_ann": float(vol),
        "cagr": float(cagr),
        "max_dd": float(dd)
    }


# ─────────────────────────────────────────────
# ✅ HAUPTFUNKTION (NEU, KOMPLETT KOMPATIBEL MIT ALPHALYZER)
# ─────────────────────────────────────────────
def tool_prices(
    ticker: str,
    start: str = "2018-01-01",
    end: str | None = None,
    adjusted: bool = True
) -> pd.DataFrame:

    try:
        asset_type = detect_asset_type(ticker)

        df = fetch_history(
            ticker=ticker,
            start=start,
            end=end,
            adjusted=adjusted
        )

        if df.empty or "close" not in df.columns:
            raise ValueError("Leere oder ungültige EOD-Daten")

        return df[["close"]].dropna()

    except Exception as e:
        print(f"❌ tool_prices FEHLER bei {ticker}: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# ✅ LEGACY WRAPPER (FÜR BESTEHENDE MODULE)
# ─────────────────────────────────────────────
def tool_prices_legacy(payload: dict) -> dict:

    t = payload.get("ticker", "AAPL")
    start = payload.get("start", "2020-01-01")
    end   = payload.get("end")

    df = fetch_history(t, start=start, end=end)
    mets = simple_metrics(df)

    return {
        "ok": True,
        "ticker": t,
        "metrics": mets,
        "history": df.reset_index().to_dict("records"),
        "tail": df.tail(5).reset_index().to_dict("records"),
        "n": len(df),
    }

