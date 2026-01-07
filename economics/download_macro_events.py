#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download / maintain macro event calendar
----------------------------------------
Phase 1: Static curated calendar (US core events)
Later: replace with FRED / Econoday / API
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

OUT_FILE = DATA_DIR / "macro_events.csv"


def build_macro_calendar():

    events = [
        # ─── CPI
        {"date": "2026-01-14", "event": "US CPI", "country": "US", "type": "Inflation"},
        {"date": "2026-02-11", "event": "US CPI", "country": "US", "type": "Inflation"},

        # ─── Jobs
        {"date": "2026-01-09", "event": "US Non-Farm Payrolls", "country": "US", "type": "Labor"},
        {"date": "2026-02-06", "event": "US Non-Farm Payrolls", "country": "US", "type": "Labor"},

        # ─── GDP
        {"date": "2026-01-29", "event": "US GDP (Q4 advance)", "country": "US", "type": "Growth"},

        # ─── FOMC
        {"date": "2026-01-29", "event": "FOMC Rate Decision", "country": "US", "type": "Rates"},
        {"date": "2026-03-18", "event": "FOMC Rate Decision", "country": "US", "type": "Rates"},
    ]

    df = pd.DataFrame(events)
    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(OUT_FILE, index=False)

    print(f"✔ Macro calendar written: {OUT_FILE}")
    print(df)


if __name__ == "__main__":
    build_macro_calendar()

