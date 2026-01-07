#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
from pathlib import Path

DEMO_DATA = Path(__file__).resolve().parent.parent / "demo_data"

def load_demo_prices(name: str) -> pd.DataFrame:
    """
    Loads demo price series (Date, Close).
    """
    path = DEMO_DATA / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path, parse_dates=["Date"])
    df = df.set_index("Date").sort_index()
    return df

