#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build pwin_states.csv per league
--------------------------------
• Input : data/<league>/team_states.csv
• Output: data/<league>/pwin_states.csv
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"

MIN_SAMPLES = 30
SHRINK_K = 20   # shrink strength towards 0.5


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def shrink(p: float, n: int, k: int = SHRINK_K) -> float:
    """Empirical Bayes shrinkage towards 0.5"""
    return (p * n + 0.5 * k) / (n + k)


def discover_leagues() -> list[str]:
    """Only treat folders as leagues if they contain team_states.csv"""
    leagues = []
    if not DATA_ROOT.exists():
        return leagues

    for p in DATA_ROOT.iterdir():
        if p.is_dir() and (p / "team_states.csv").exists():
            leagues.append(p.name)

    return sorted(leagues)


# ─────────────────────────────────────────────
# CORE
# ─────────────────────────────────────────────

def build_pwin_states(league: str):

    data_dir = DATA_ROOT / league
    in_file  = data_dir / "team_states.csv"
    out_file = data_dir / "pwin_states.csv"

    print(f"\n🧮 Building pwin_states: {league.upper()}")

    if not in_file.exists():
        print(f"⚠️ Missing {in_file}")
        return

    df = pd.read_csv(in_file)

    if df.empty:
        print("⚠️ team_states.csv is empty")
        return

    required = {"state", "win", "draw"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"{in_file} missing columns: {sorted(missing)}")

    grp = (
        df.groupby("state")
          .agg(
              samples=("win", "count"),
              wins=("win", "sum"),
              draws=("draw", "sum"),
          )
          .reset_index()
    )

    grp["p_win_raw"]  = grp["wins"] / grp["samples"]
    grp["p_draw_raw"] = grp["draws"] / grp["samples"]

    # Use NaN (not None) for numeric columns
    grp["p_win"] = np.where(
        grp["samples"] >= MIN_SAMPLES,
        grp.apply(lambda r: shrink(float(r["p_win_raw"]), int(r["samples"])), axis=1),
        np.nan
    )

    grp["p_draw"] = np.where(
        grp["samples"] >= MIN_SAMPLES,
        grp["p_draw_raw"].astype(float),
        np.nan
    )

    # Confidence: if p_win NaN, treat as neutral 0.5 (so confidence -> 0)
    grp["confidence"] = grp["samples"] * (grp["p_win"].fillna(0.5) - 0.5).abs()

    grp = grp.sort_values("samples", ascending=False)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    grp.to_csv(out_file, index=False)

    print(f"✔ {out_file} ({len(grp)} states)")
    print(grp[["state", "samples", "p_win", "p_draw", "confidence"]].head(12))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    # CLI:
    # python3 pwin_states.py epl
    # python3 pwin_states.py laliga
    # python3 pwin_states.py seriea

    if len(sys.argv) > 1:
        leagues = [sys.argv[1].strip().lower()]
    else:
        leagues = discover_leagues()

    if not leagues:
        print("⚠️ No leagues found (expected data/<league>/team_states.csv).")
        return

    for lg in leagues:
        build_pwin_states(lg)

    print("\n🏁 Done.")


if __name__ == "__main__":
    main()

