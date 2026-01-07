#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import asyncio, logging, httpx, backoff
from httpx import Limits, PoolTimeout, HTTPStatusError

HEADERS = {"accept": "application/json"}
BASE = "https://eodhistoricaldata.com/api"

@backoff.on_exception(backoff.expo, (HTTPStatusError, PoolTimeout, httpx.ReadTimeout), max_time=30)
async def _get(clt, url, params): 
    r = await clt.get(url, params=params)
    r.raise_for_status()
    return r.json()

async def fetch_prices(tickers, key, start, end, period="d"):
    limits = Limits(max_connections=200, max_keepalive_connections=50)
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, limits=limits) as clt:
        res = await asyncio.gather(
            *(_get(clt, f"{BASE}/eod/{tk}",
                   {"api_token": key, "from": start, "to": end,
                    "period": period, "fmt": "json", "adjusted": "splitdiv"})
              for tk in tickers),
            return_exceptions=True
        )
    out = {}
    for tk, js in zip(tickers, res):
        if not isinstance(js, Exception): out[tk] = js
        else: logging.warning(f"Fetch error {tk}: {js}")
    return out

async def fetch_names(tickers, key):
    limits = Limits(max_connections=100, max_keepalive_connections=30)
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, limits=limits) as clt:
        res = await asyncio.gather(
            *(_get(clt, f"{BASE}/fundamentals/{tk}",
                   {"api_token": key, "fmt": "json"}) for tk in tickers),
            return_exceptions=True
        )
    names = {}
    for tk, js in zip(tickers, res):
        if isinstance(js, Exception): continue
        g = js.get("General", {})
        names[tk] = g.get("Name") or g.get("CodeName") or g.get("Code") or tk
    return names

