#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# tools/wm_tipp/scoring.py
from __future__ import annotations
import pandas as pd
from typing import Dict

from .config import TEAMS
from .elo_loader import load_world_elo
from .p_up_loader import load_all_p_up


# -------------------------------------------------------------------
# LOAD ELO + P_UP
# -------------------------------------------------------------------

def load_elo_scores() -> Dict[str, float]:
    """Lädt Elo Ratings."""
    return load_world_elo()


def load_momentum_p_up() -> Dict[str, float]:
    """Lädt p_up Momentum Scores.
       Falls keine Daten gefunden → default 0.50.
    """
    return load_all_p_up()


# -------------------------------------------------------------------
# FAVORITEN-SCORE (Standard)
# -------------------------------------------------------------------
def compute_favorite_table(date_key: str | None = None) -> pd.DataFrame:
    """
    Gibt Favoritenranking zurück.
    Formel wie früher:
        fav_score = 0.70 * elo_norm + 0.30 * p_up

    p_up = 0.50 wenn keine Momentum-Daten geladen werden konnten.
    """

    team_codes = [t.code for t in TEAMS]

    # Elo
    elo_map = load_elo_scores()

    # p_up (heute meistens 0.5)
    p_up_map = load_momentum_p_up()

    df = pd.DataFrame(index=team_codes)
    df.index.name = "Team"

    df["elo"] = [elo_map.get(code, 1600.0) for code in team_codes]
    df["p_up"] = [p_up_map.get(code, 0.50) for code in team_codes]

    # Elo normalisieren
    df["elo_norm"] = df["elo"] / df["elo"].max()

    # Klassischer Favoriten-Score
    df["fav_score"] = (
        0.70 * df["elo_norm"] +
        0.30 * df["p_up"]
    )

    df = df.sort_values("fav_score", ascending=False)

    return df[["elo", "p_up", "elo_norm", "fav_score"]]

