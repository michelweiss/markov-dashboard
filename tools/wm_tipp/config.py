#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# tools/wm_tipp/config.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Team:
    code: str
    name: str
    group: str


# ───────────────────────────────────────────────
# OFFIZIELLE AUSLOSUNG – FIFA WM 2026
# 12 Gruppen (A–L), je 4 Teams → total 48
# Platzhalter für offene Quali inkludiert
# ───────────────────────────────────────────────

TEAMS: List[Team] = [

    # GROUP A
    Team("MEX", "Mexico", "A"),
    Team("RSA", "South Africa", "A"),
    Team("KOR", "Korea Republic", "A"),
    Team("EPO_D", "EU Playoff D Winner", "A"),

    # GROUP B
    Team("CAN", "Canada", "B"),
    Team("EPO_A", "EU Playoff A Winner", "B"),
    Team("QAT", "Qatar", "B"),
    Team("SUI", "Switzerland", "B"),

    # GROUP C
    Team("BRA", "Brazil", "C"),
    Team("MAR", "Morocco", "C"),
    Team("HAI", "Haiti", "C"),
    Team("SCO", "Scotland", "C"),

    # GROUP D
    Team("USA", "USA", "D"),
    Team("PAR", "Paraguay", "D"),
    Team("AUS", "Australia", "D"),
    Team("EPO_C", "EU Playoff C Winner", "D"),

    # GROUP E
    Team("GER", "Germany", "E"),
    Team("CUW", "Curaçao", "E"),
    Team("CIV", "Ivory Coast", "E"),
    Team("ECU", "Ecuador", "E"),

    # GROUP F
    Team("NED", "Netherlands", "F"),
    Team("JPN", "Japan", "F"),
    Team("EPO_B", "EU Playoff B Winner", "F"),
    Team("TUN", "Tunisia", "F"),

    # GROUP G
    Team("BEL", "Belgium", "G"),
    Team("EGY", "Egypt", "G"),
    Team("IRN", "IR Iran", "G"),
    Team("NZL", "New Zealand", "G"),

    # GROUP H
    Team("ESP", "Spain", "H"),
    Team("CPV", "Cape Verde", "H"),
    Team("KSA", "Saudi Arabia", "H"),
    Team("URU", "Uruguay", "H"),

    # GROUP I
    Team("FRA", "France", "I"),
    Team("SEN", "Senegal", "I"),
    Team("FIFA_PO2", "FIFA Playoff 2 Winner", "I"),
    Team("NOR", "Norway", "I"),

    # GROUP J
    Team("ARG", "Argentina", "J"),
    Team("ALG", "Algeria", "J"),
    Team("AUT", "Austria", "J"),
    Team("JOR", "Jordan", "J"),

    # GROUP K
    Team("POR", "Portugal", "K"),
    Team("FIFA_PO1", "FIFA Playoff 1 Winner", "K"),
    Team("UZB", "Uzbekistan", "K"),
    Team("COL", "Colombia", "K"),

    # GROUP L
    Team("ENG", "England", "L"),
    Team("CRO", "Croatia", "L"),
    Team("GHA", "Ghana", "L"),
    Team("PAN", "Panama", "L"),

]


# ───────────────────────────────────────────────
# GROUP HELPERS
# ───────────────────────────────────────────────

GROUPS = sorted({t.group for t in TEAMS})

def teams_by_group() -> Dict[str, List[Team]]:
    result: Dict[str, List[Team]] = {g: [] for g in GROUPS}
    for t in TEAMS:
        result[t.group].append(t)
    return result

