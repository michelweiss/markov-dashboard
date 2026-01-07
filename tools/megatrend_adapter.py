#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import httpx
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json
import time

API_KEY = Path("/Users/michelweiss/Documents/Python_for_Finance/api_token.txt").read_text().strip()
BASE_PRICE_URL = "https://eodhd.com/api/eod"
BASE_FUND_URL  = "https://eodhd.com/api/fundamentals"

CACHE_DIR = Path("/Users/michelweiss/Documents/Python_for_Finance/megatrend_cache")
CACHE_DIR.mkdir(exist_ok=True)

CACHE_TTL = 6 * 3600  # 6 Stunden


def _make_symbol(ticker: str) -> str:
    """
    Wenn der Ticker bereits einen Exchange-Suffix hat (AAPL.US, MC.PA, ABBN.SW usw.),
    NICHT erneut '.US' anhängen. Sonst Standard: '.US'.
    """
    ticker = ticker.strip()
    if "." in ticker:
        return ticker  # schon voll qualifiziert
    return f"{ticker}.US"


def _cache_get(name: str):
    f = CACHE_DIR / name
    if not f.exists():
        return None
    if time.time() - f.stat().st_mtime > CACHE_TTL:
        return None
    try:
        return pd.read_parquet(f)
    except Exception:
        return None


def _cache_set(name: str, df: pd.DataFrame):
    try:
        df.to_parquet(CACHE_DIR / name)
    except Exception:
        pass


def get_prices(ticker: str, years: int = 2) -> pd.DataFrame:
    cache_name = f"px_{ticker}_{years}y.parquet"
    cached = _cache_get(cache_name)
    if cached is not None:
        return cached.copy()

    start = (datetime.today() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
    sym = _make_symbol(ticker)
    url = f"{BASE_PRICE_URL}/{sym}"
    params = {
        "api_token": API_KEY,
        "fmt": "json",
        "from": start,
    }

    try:
        r = httpx.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if "date" not in df or "close" not in df:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        _cache_set(cache_name, df)
        return df.copy()
    except Exception:
        # Leeren DF zurückgeben, statt Exception durchzureichen
        return pd.DataFrame()


def get_fundamentals(ticker: str) -> dict:
    cache_name = f"fund_{ticker}.json"
    f = CACHE_DIR / cache_name

    if f.exists() and (time.time() - f.stat().st_mtime < 24 * 3600):
        try:
            return json.loads(f.read_text())
        except Exception:
            pass

    sym = _make_symbol(ticker)
    url = f"{BASE_FUND_URL}/{sym}"
    params = {"api_token": API_KEY}

    try:
        r = httpx.get(url, params=params, timeout=20)
        r.raise_for_status()
        # Manche Antworten sind leer / HTML → JSON-Fehler abfangen
        try:
            data = r.json()
        except Exception:
            data = {}
        f.write_text(json.dumps(data))
        return data
    except Exception:
        return {}

