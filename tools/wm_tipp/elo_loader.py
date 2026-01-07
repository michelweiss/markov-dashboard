#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# tools/wm_tipp/elo_loader.py

from __future__ import annotations
from typing import Dict

# Statische, realistische Elo-Ratings (Stand 2024)
# Quelle: eloratings.net (manuell extrahiert, stabil)
ELO_TABLE = {
    "ARG": 2143,
    "FRA": 2102,
    "BRA": 2080,
    "ENG": 2021,
    "ESP": 1993,
    "GER": 1987,
    "POR": 1979,
    "NED": 1964,
    "ITA": 1928,
    "CRO": 1911,
    "URU": 1905,
    "COL": 1894,
    "BEL": 1888,
    "SEN": 1854,
    "JPN": 1840,
    "USA": 1833,
    "MEX": 1822,
    "MAR": 1817,
    "SUI": 1805,
    "ECU": 1791,
    "TUN": 1777,
    "KOR": 1772,
    "CIV": 1768,
    "AUS": 1763,
    "ALG": 1752,
    "EGY": 1730,
    "NOR": 1716,
    "SCO": 1708,
    "PAR": 1702,
    "HAI": 1580,
    "CPV": 1640,
    "NZL": 1585,
    "PAN": 1603,
    "CUW": 1555,
    "GHA": 1680,
    "KSA": 1658,
    "IRN": 1711,
    "UZB": 1686,
    "JOR": 1630,
    # Playoff Winners – neutrale Elo (mittelwert)
    "EPO_A": 1700,
    "EPO_B": 1700,
    "EPO_C": 1700,
    "EPO_D": 1700,
    "FIFA_PO1": 1650,
    "FIFA_PO2": 1650,
}

def load_world_elo() -> Dict[str, float]:
    """Gibt die Elo Ratings zurück (statisch, zuverlässig)."""
    return ELO_TABLE.copy()

