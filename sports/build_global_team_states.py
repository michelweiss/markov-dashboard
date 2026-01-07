#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"

LEAGUES = ["epl", "laliga", "seriea", "ligue1"]
OUT_FILE = DATA_ROOT / "team_states.csv"

dfs = []

for lg in LEAGUES:
    file = DATA_ROOT / lg / "team_states.csv"
    if not file.exists():
        print(f"⚠️ missing {file}")
        continue

    df = pd.read_csv(file)
    df["league"] = lg   # optional, nur für Debug
    dfs.append(df)

if not dfs:
    raise RuntimeError("No team_states found")

out = pd.concat(dfs, ignore_index=True)
out.to_csv(OUT_FILE, index=False)

print(f"✔ global team_states.csv written ({len(out)} rows)")
print(out.state.value_counts())

