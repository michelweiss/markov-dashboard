#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "event_states.csv"
OUT_FILE = DATA_DIR / "pwin_events.csv"

SHRINK_K = 20

def shrink(p: float, n: int, k: int = SHRINK_K) -> float:
    return (p * n + 0.5 * k) / (n + k)

def build_pwin_events():
    df = pd.read_csv(IN_FILE)

    rows = []
    for (ev, state), g in df.groupby(["event", "state"]):
        n = len(g)
        wins = int(g["outcome_up"].sum())
        p_raw = wins / n if n else 0.5
        p = shrink(p_raw, n)

        rows.append({
            "event": ev,
            "state": state,
            "samples": n,
            "wins": wins,
            "p_raw": round(p_raw, 4),
            "p_shrunk": round(p, 4),
        })

    out = pd.DataFrame(rows).sort_values(["event", "samples"], ascending=[True, False]).reset_index(drop=True)
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ pwin_events written: {OUT_FILE}")
    print(out.tail(30))

if __name__ == "__main__":
    build_pwin_events()

