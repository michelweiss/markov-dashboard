#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build NFP probabilities (3-class Markov)
---------------------------------------
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"

IN_FILE  = DATA_DIR / "event_states_nfp.csv"
OUT_FILE = DATA_DIR / "pwin_nfp.csv"

SHRINK_K = 20


def shrink(p, n, k=SHRINK_K):
    return (p * n + (1/3) * k) / (n + k)


def build():

    df = pd.read_csv(IN_FILE)

    rows = []

    for (state, outcome), g in df.groupby(["state", "outcome"]):
        n_state = len(df[df.state == state])
        n = len(g)

        p_raw = n / n_state
        p = shrink(p_raw, n_state)

        rows.append({
            "state": state,
            "outcome": outcome,
            "samples": n_state,
            "p_raw": round(p_raw, 4),
            "p_shrunk": round(p, 4),
        })

    out = (
        pd.DataFrame(rows)
        .sort_values(["state", "p_shrunk"], ascending=[True, False])
    )

    out.to_csv(OUT_FILE, index=False)

    print(f"✔ NFP probabilities written: {OUT_FILE}")
    print(out.tail())


if __name__ == "__main__":
    build()

