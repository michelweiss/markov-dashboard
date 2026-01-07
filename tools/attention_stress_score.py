#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

# ─────────────────────────────────────────────
# PATH PATCH
# ─────────────────────────────────────────────
MARKOV_ROOT = Path(__file__).resolve().parents[1]
if str(MARKOV_ROOT) not in sys.path:
    sys.path.insert(0, str(MARKOV_ROOT))

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
SNAP_DIR = MARKOV_ROOT / "data" / "snapshots"

ATTENTION_FILE = SNAP_DIR / "attention_weekly_only.csv"
STRESS_FILE    = SNAP_DIR / "stress_response_t1_core.csv"

ALPHA = 1.0   # Gewicht Stress-Response

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
print("📥 Loading attention + stress data …")

att = pd.read_csv(ATTENTION_FILE, index_col=0)
stress = pd.read_csv(STRESS_FILE, index_col=0)

# Nur Core-Titel (sicher)
att_core = att[att["attention_tier"] == "T1_core"].copy()

# Join
df = att_core.join(stress, how="left")

# ─────────────────────────────────────────────
# SCORE
# ─────────────────────────────────────────────
df["final_score"] = (
    df["ap_score"]
    + ALPHA * df["stress_delta_2sigma"].fillna(0.0)
)

df = df.sort_values("final_score", ascending=False)

# ─────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────
print("\n🏆 STRESS-ADJUSTED ATTENTION SCORE (T1_core)")
print(
    df[
        [
            "ap_score",
            "p_up",
            "stress_delta_2sigma",
            "final_score"
        ]
    ]
    .round(3)
)

out_fp = SNAP_DIR / "attention_stress_score_t1_core.csv"
df.to_csv(out_fp)
print(f"\n💾 Saved to {out_fp}")

