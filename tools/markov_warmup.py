#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# tools/markov_warmup.py
from __future__ import annotations
import pandas as pd


def select_markov_warmup(
    df: pd.DataFrame,
    *,
    asof: pd.Timestamp,
    min_years: float = 2.0,
    max_years: float = 3.0,
    hard_start: str | None = None,
) -> pd.DataFrame:

    # ─────────────────────────────────────────
    # 1️⃣ Index TZ-sicher machen
    # ─────────────────────────────────────────
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame Index muss DatetimeIndex sein")

    if df.index.tz is None:
        df = df.tz_localize("UTC")

    if asof.tzinfo is None:
        asof = asof.tz_localize(df.index.tz)
    else:
        asof = asof.tz_convert(df.index.tz)

    # ─────────────────────────────────────────
    # 2️⃣ Hard-Start korrekt (OHNE tz=…)
    # ─────────────────────────────────────────
    if hard_start:
        hard_start_ts = pd.Timestamp(hard_start)

        if hard_start_ts.tzinfo is None:
            hard_start_ts = hard_start_ts.tz_localize(df.index.tz)
        else:
            hard_start_ts = hard_start_ts.tz_convert(df.index.tz)

        df = df[df.index >= hard_start_ts]

    # ─────────────────────────────────────────
    # 3️⃣ Rolling Warm-up Window
    # ─────────────────────────────────────────
    max_start = asof - pd.DateOffset(years=max_years)
    min_start = asof - pd.DateOffset(years=min_years)

    df = df[(df.index >= max_start) & (df.index <= asof)]

    if len(df) < 30:
        raise ValueError("Warm-up zu kurz (<30 Bars)")

    return df

