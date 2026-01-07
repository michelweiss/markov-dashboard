#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# tools/wm_tipp/sim_48.py
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from .config import TEAMS, GROUPS, teams_by_group
from .scoring import compute_favorite_table


# ─────────────────────────────────────────────
# Hilfsmethoden
# ─────────────────────────────────────────────

def _simulate_group_order(
    team_codes: List[str],
    strength: Dict[str, float],
    rng: np.random.Generator
) -> List[str]:
    """
    Simuliert eine Gruppenplatzierung von 1–4,
    gewichtet nach 'strength'.
    """
    scores = []
    for code in team_codes:
        scores.append((code, strength.get(code, 1.0) * rng.normal(1.0, 0.2)))
    ranked = sorted(scores, key=lambda x: x[1], reverse=True)
    return [c for c, _ in ranked]


def _pair_round(teams: List[str]) -> List[Tuple[str, str]]:
    """
    Paart Teams sequentiell zu KO-Duellen:
    [A,B,C,D] → (A vs B), (C vs D)
    """
    n = len(teams)
    if n % 2 != 0:
        raise ValueError(f"KO-Runde hat ungerade Anzahl Teams: {n}")
    return [(teams[i], teams[i + 1]) for i in range(0, n, 2)]


def _draw_knockout_winner(
    team_a: str,
    team_b: str,
    strength: Dict[str, float],
    rng: np.random.Generator,
    p_up_map: Dict[str, float] | None = None,
) -> str:
    """
    Ziehe Gewinner eines KO-Duells, mit Momentum-Bias (p_up).
    """

    sa = strength.get(team_a, 1.0)
    sb = strength.get(team_b, 1.0)

    if p_up_map is None:
        p_up_map = {}

    pa = p_up_map.get(team_a, 0.50)
    pb = p_up_map.get(team_b, 0.50)

    adj_a = 1.0 + 0.15 * (pa - 0.5)
    adj_b = 1.0 + 0.15 * (pb - 0.5)

    eff_a = sa * adj_a
    eff_b = sb * adj_b

    if eff_a <= 0 and eff_b <= 0:
        p = 0.5
    else:
        p = eff_a / (eff_a + eff_b)

    return team_a if rng.random() < p else team_b


def _simulate_knockout_32(
    teams_32: List[str],
    strength: Dict[str, float],
    rng: np.random.Generator,
    p_up_map: Dict[str, float],
) -> str:
    """
    Simuliert das KO-Turnier:
    32 → 16 → 8 → 4 → 2 → 1 Champion.
    """
    round_teams = teams_32[:]

    while len(round_teams) > 1:
        matches = _pair_round(round_teams)
        winners = [
            _draw_knockout_winner(a, b, strength, rng, p_up_map)
            for a, b in matches
        ]
        round_teams = winners

    return round_teams[0]


# ─────────────────────────────────────────────
# Hauptfunktion: Simulation WM-2026
# ─────────────────────────────────────────────

def simulate_world_cup_48(
    n_sims: int = 20_000,
    date_key: str | None = None,
    use_fav_score: bool = True,
    random_seed: int = 123,
) -> pd.DataFrame:

    # 1) Stärke & p_up laden
    fav_df = compute_favorite_table(date_key)

    # ❗ WICHTIG: KEIN "strength" verwenden — wir nutzen fav_score
    strength = (
        fav_df["fav_score"].to_dict()
        if use_fav_score
        else fav_df["elo"].to_dict()
    )

    # p_up Map (heute alles 0.5)
    p_up_map = fav_df["p_up"].to_dict()

    # 2) Setup
    rng = np.random.default_rng(random_seed)
    team_list = list(fav_df.index)

    # Champion Counter
    champion_counts = {t: 0 for t in team_list}

    # 3) Gruppeninfos
    groups = teams_by_group()

    # 4) Monte-Carlo
    for _ in range(n_sims):

        # 4.1 Gruppen simulieren
        group_rankings: Dict[str, List[str]] = {}
        third_places: List[str] = []

        for g, team_objs in groups.items():
            codes = [t.code for t in team_objs]
            placed = _simulate_group_order(codes, strength, rng)

            group_rankings[g] = placed
            third_places.append(placed[2])

        # 4.2 Top 8 Dritte auswählen (nach Strength)
        third_strength = sorted(
            third_places,
            key=lambda x: strength.get(x, 1.0),
            reverse=True,
        )
        best_thirds = third_strength[:8]

        # 4.3 1. + 2. + beste Dritte → 32 Teams
        teams_32: List[str] = []
        for g, placed in group_rankings.items():
            teams_32.append(placed[0])  # Sieger
            teams_32.append(placed[1])  # Zweiter
        teams_32.extend(best_thirds)

        if len(teams_32) != 32:
            continue

        # 4.4 KO simulieren
        champion = _simulate_knockout_32(teams_32, strength, rng, p_up_map)
        champion_counts[champion] += 1

    # 5) Output DataFrame bauen
    out = fav_df.copy()
    out["sim_champion_count"] = [champion_counts[c] for c in out.index]
    out["sim_champion_prob"] = out["sim_champion_count"] / n_sims
    out = out.sort_values("sim_champion_prob", ascending=False)

    return out

