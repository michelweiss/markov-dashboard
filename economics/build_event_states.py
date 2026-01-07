#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE = DATA_DIR / "macro_actuals.csv"
OUT_FILE = DATA_DIR / "event_states.csv"


def build_states():
    df = pd.read_csv(IN_FILE, parse_dates=["date"]).sort_values(["event", "date"]).reset_index(drop=True)

    out_rows = []

    for ev, g in df.groupby("event", sort=False):
        g = g.sort_values("date").copy()

        # Rolling window je nach Frequenz
        win = 6
        if ev in ("US GDP",):
            win = 4     # quarterly: 4 quarters makes more sense
        if ev in ("FOMC",):
            win = 6     # ok

        g["trend_up"] = g["actual"].rolling(win).mean().diff().gt(0).astype(int)
        g["last_surprise_pos"] = g["surprise"].shift(1).gt(0).astype(int)

        g = g.dropna().copy()

        g["state"] = list(zip(g["trend_up"], g["last_surprise_pos"]))
        g["outcome_up"] = (g["surprise"] > 0).astype(int)  # for FOMC this is "rate change > 0" (we’ll do discrete later)

        out_rows.append(g[["date", "event", "state", "outcome_up"]])

    out = pd.concat(out_rows, ignore_index=True).sort_values(["event", "date"]).reset_index(drop=True)
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ Event states written: {OUT_FILE}")
    print(out.tail(20))


if __name__ == "__main__":
    build_states()

