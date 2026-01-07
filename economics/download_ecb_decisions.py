#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ECB rate decisions (manual / SDW-based)
--------------------------------------
Discrete ECB Governing Council decisions
Outcome: -0.25 / 0.00 / +0.25
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"
DATA_DIR.mkdir(exist_ok=True)

OUT_FILE = DATA_DIR / "ecb_decisions.csv"


def build_ecb_decisions():

    data = [
        # date, delta
        ("2014-09-04", -0.10),
        ("2015-12-03", -0.10),
        ("2016-03-10", -0.05),
        ("2022-07-21", +0.50),
        ("2022-09-08", +0.75),
        ("2022-10-27", +0.75),
        ("2022-12-15", +0.50),
        ("2023-02-02", +0.50),
        ("2023-03-16", +0.50),
        ("2023-05-04", +0.25),
        ("2023-06-15", +0.25),
        ("2023-07-27", +0.25),
        ("2023-09-14", 0.00),
        ("2023-10-26", 0.00),
    ]

    df = pd.DataFrame(data, columns=["date", "actual"])
    df["date"] = pd.to_datetime(df["date"])

    df["event"] = "ECB"
    df["consensus"] = 0.0
    df["surprise"] = df["actual"]

    df.to_csv(OUT_FILE, index=False)
    print(f"✔ ECB decisions written: {OUT_FILE}")
    print(df.tail())


if __name__ == "__main__":
    build_ecb_decisions()

