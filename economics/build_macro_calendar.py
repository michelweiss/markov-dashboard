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

        # ───────────────── CPI ─────────────────
        {
            "date": "2026-01-14",
            "event": "US CPI",
            "label": "US CPI",
            "country": "US",
            "type": "Inflation",
            "freq": "Monthly",
        },
        {
            "date": "2026-02-11",
            "event": "US CPI",
            "label": "US CPI",
            "country": "US",
            "type": "Inflation",
            "freq": "Monthly",
        },

        # ───────────────── NFP ─────────────────
        {
            "date": "2026-01-09",
            "event": "US NFP",
            "label": "US Non-Farm Payrolls",
            "country": "US",
            "type": "Labor",
            "freq": "Monthly",
        },
        {
            "date": "2026-02-06",
            "event": "US NFP",
            "label": "US Non-Farm Payrolls",
            "country": "US",
            "type": "Labor",
            "freq": "Monthly",
        },

        # ───────────────── GDP ─────────────────
        {
            "date": "2026-01-29",
            "event": "US GDP",
            "label": "US GDP (Q4 advance)",
            "country": "US",
            "type": "Growth",
            "freq": "Quarterly",
            "release": "Advance",
        },

        # ───────────────── FOMC ─────────────────
        {
            "date": "2026-01-29",
            "event": "FOMC",
            "label": "FOMC Rate Decision",
            "country": "US",
            "type": "Rates",
            "freq": "Meeting",
        },
        {
            "date": "2026-03-18",
            "event": "FOMC",
            "label": "FOMC Rate Decision",
            "country": "US",
            "type": "Rates",
            "freq": "Meeting",
        },

        # ───────────────── EU CPI ─────────────────
        {
            "date": "2026-01-22",
            "event": "EU CPI",
            "label": "Eurozone CPI (HICP YoY)",
            "country": "EU",
            "type": "Inflation",
            "freq": "Monthly",
        },
        
        # ───────────────── EU GDP ─────────────────
        {
            "date": "2026-01-30",
            "event": "EU GDP",
            "label": "Eurozone GDP (QoQ)",
            "country": "EU",
            "type": "Growth",
            "freq": "Quarterly",
        },
        
        # ───────────────── ECB ─────────────────
        {
            "date": "2026-01-23",
            "event": "ECB",
            "label": "ECB Rate Decision",
            "country": "EU",
            "type": "Rates",
            "freq": "Meeting",
        },

        # ───────────────── SNB ─────────────────
        {
            "date": "2026-03-19",
            "event": "SNB",
            "label": "SNB Policy Rate Decision",
            "country": "CH",
            "type": "Rates",
            "freq": "Meeting",
        },

        # ───────────────── CH CPI ─────────────────
        {
            "date": "2026-01-14",
            "event": "CH CPI",
            "label": "Switzerland CPI (YoY)",
            "country": "CH",
            "type": "Inflation",
            "freq": "Monthly",
        },
        
        # ───────────────── CH GDP ─────────────────
        {
            "date": "2026-03-05",
            "event": "CH GDP",
            "label": "Switzerland GDP (QoQ)",
            "country": "CH",
            "type": "Growth",
            "freq": "Quarterly",
        },


    ]

    df = pd.DataFrame(events)
    df["date"] = pd.to_datetime(df["date"])

    # saubere Sortierung & stabile Struktur
    df = (
        df.sort_values("date")
          .reset_index(drop=True)
    )

    df.to_csv(OUT_FILE, index=False)

    print(f"✔ Macro calendar written: {OUT_FILE}")
    print(df)


if __name__ == "__main__":
    build_macro_calendar()

