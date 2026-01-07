#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

import sys
import argparse
from pathlib import Path

import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
# PATH PATCH (wie überall bei dir)
# ─────────────────────────────────────────────
MARKOV_ROOT = Path(__file__).resolve().parents[1]  # …/Markov
if str(MARKOV_ROOT) not in sys.path:
    sys.path.insert(0, str(MARKOV_ROOT))

from tools.attention_persistence import compute_attention_persistence


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--universe", type=str, default="nasdaq100")
parser.add_argument("--top-k", type=int, default=10)
parser.add_argument("--window", type=int, default=12)
parser.add_argument("--thr-core", type=float, default=0.55)
parser.add_argument("--thr-tactical", type=float, default=0.40)
args = parser.parse_args()

UNIVERSE = args.universe.lower()

SNAP_DIR = MARKOV_ROOT / "data" / "snapshots" / UNIVERSE
SNAP_DIR.mkdir(parents=True, exist_ok=True)

SNAPSHOT_FP = SNAP_DIR / f"snapshots_{UNIVERSE}_weekly.csv"

if not SNAPSHOT_FP.exists():
    raise FileNotFoundError(f"Snapshot nicht gefunden: {SNAPSHOT_FP}")

print("📥 Loading weekly snapshots …")
df = pd.read_csv(SNAPSHOT_FP, parse_dates=["date"])
print(f"   rows: {len(df):,}")


# ─────────────────────────────────────────────
# ATTENTION PERSISTENCE
# ─────────────────────────────────────────────
print("🧠 Computing Weekly Attention Persistence …")

ap = compute_attention_persistence(
    df,
    freq="weekly",
    top_k=args.top_k,
    window=args.window,
    weighted=False
)

latest = (
    ap
    .sort_values("date")
    .groupby("Ticker")
    .tail(1)
    .copy()
)

# ─────────────────────────────────────────────
# TIERING (statt eligible)
# ─────────────────────────────────────────────
def attention_tier(ap_score: float) -> str:
    if ap_score >= args.thr_core:
        return "T1_core"
    if ap_score >= args.thr_tactical:
        return "T2_tactical"
    if ap_score > 0:
        return "T3_watch"
    return "ignore"


latest["attention_tier"] = latest["ap_score"].apply(attention_tier)

tier_order = {
    "T1_core": 0,
    "T2_tactical": 1,
    "T3_watch": 2,
    "ignore": 3,
}

latest["tier_rank"] = latest["attention_tier"].map(tier_order)

latest = latest.sort_values(
    ["tier_rank", "ap_score", "p_up"],
    ascending=[True, False, False]
)

# ─────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────
print(f"\n🏆 WEEKLY ATTENTION LEADERS ({UNIVERSE.upper()})")
print(
    latest[["p_up", "rank", "ap_score", "attention_tier"]]
    .head(20)
    .round(3)
)

print("\n📊 Tier Summary")
print(latest["attention_tier"].value_counts())

out_fp = SNAP_DIR / "attention_weekly_only.csv"
latest.to_csv(out_fp)
print(f"\n💾 Saved to {out_fp}")

