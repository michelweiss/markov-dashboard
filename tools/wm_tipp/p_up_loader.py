#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# tools/wm_tipp/p_up_loader.py
from __future__ import annotations

import httpx
import pandas as pd
import re
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List

CACHE_PATH = Path(__file__).resolve().parent / "p_up_cache.csv"


# ------------------------------------------------------------
# Teamnamen-Mapping für eloratings.net
# ------------------------------------------------------------
TEAM_NAME_MAP = {
    # GROUP A – Mexico, South Africa, Korea Republic + Playoff-D
    "Mexico": "Mexico",
    "South Africa": "South-Africa",
    "Republic of Korea": "South-Korea",

    # GROUP B
    "Canada": "Canada",
    "Qatar": "Qatar",
    "Switzerland": "Switzerland",

    # GROUP C
    "Brazil": "Brazil",
    "Morocco": "Morocco",
    "Haiti": "Haiti",
    "Scotland": "Scotland",

    # GROUP D
    "USA": "United-States",
    "Paraguay": "Paraguay",
    "Australia": "Australia",

    # GROUP E
    "Germany": "Germany",
    "Curaçao": "Curacao",
    "Ivory Coast": "Ivory-Coast",
    "Ecuador": "Ecuador",

    # GROUP F
    "Netherlands": "Netherlands",
    "Japan": "Japan",
    "Tunisia": "Tunisia",

    # GROUP G
    "Belgium": "Belgium",
    "Egypt": "Egypt",
    "IR Iran": "Iran",
    "New Zealand": "New-Zealand",

    # GROUP H
    "Spain": "Spain",
    "Cape Verde": "Cape-Verde",
    "Saudi Arabia": "Saudi-Arabia",
    "Uruguay": "Uruguay",

    # GROUP I
    "France": "France",
    "Senegal": "Senegal",
    "Norway": "Norway",

    # GROUP J
    "Argentina": "Argentina",
    "Algeria": "Algeria",
    "Austria": "Austria",
    "Jordan": "Jordan",

    # GROUP K
    "Portugal": "Portugal",
    "Uzbekistan": "Uzbekistan",
    "Colombia": "Colombia",

    # GROUP L
    "England": "England",
    "Croatia": "Croatia",
    "Ghana": "Ghana",
    "Panama": "Panama",
}


# ------------------------------------------------------------
# PLAYOFF-PFADE (UEFA + FIFA Playoffs)
# ------------------------------------------------------------
PLAYOFF_PATHS = {
    "EU-Playoff-A-Winner": [
        "Italy", "Northern-Ireland", "Wales", "Bosnia-and-Herzegovina"
    ],
    "EU-Playoff-B-Winner": [
        "Ukraine", "Sweden", "Poland", "Albania"
    ],
    "EU-Playoff-C-Winner": [
        "Turkey", "Romania", "Slovakia", "Kosovo"
    ],
    "EU-Playoff-D-Winner": [
        "Denmark", "North-Macedonia", "Czech-Republic", "Republic-of-Ireland"
    ],

    # FIFA INTERCONTINENTAL PLAYOFFS
    "FIFA-Playoff-1-Winner": [
        "DR-Congo", "Jamaica", "New-Caledonia"
    ],
    "FIFA-Playoff-2-Winner": [
        "Iraq", "Bolivia", "Suriname"
    ],
}


# ------------------------------------------------------------
# Match-Result parser
# ------------------------------------------------------------
def parse_result(score: str) -> str | None:
    m = re.match(r"(\d+)[^\d]+(\d+)", score)
    if not m:
        return None

    g_for = int(m.group(1))
    g_against = int(m.group(2))

    if g_for > g_against:
        return "W"
    if g_for < g_against:
        return "L"
    return "D"


# ------------------------------------------------------------
# Scraper für eloratings.net
# ------------------------------------------------------------
def fetch_last_matches(team: str, n_games: int = 20) -> pd.DataFrame:

    url = f"https://eloratings.net/{team}"

    try:
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️ Fehler beim Laden von {team}: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")

    if table is None:
        print(f"⚠️ Keine Daten für {team}")
        return pd.DataFrame()

    rows = table.find_all("tr")[1:]  # skip header

    data = []
    for row in rows[:n_games]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        date = cols[0].text.strip()
        opponent = cols[2].text.strip()
        score = cols[3].text.strip()
        result = parse_result(score)

        if result is None:
            continue

        data.append({
            "date": date,
            "opponent": opponent,
            "result": result,
        })

    return pd.DataFrame(data)


# ------------------------------------------------------------
# p_up aus Spielhistorie berechnen
# ------------------------------------------------------------
def compute_p_up(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.50

    wins = (df["result"] == "W").sum()
    draws = (df["result"] == "D").sum()
    games = len(df)

    return (wins + 0.5 * draws) / games


# ------------------------------------------------------------
# Hauptfunktion: p_up Werte für ALLE Teams
# ------------------------------------------------------------
def load_all_p_up() -> Dict[str, float]:

    # Falls Cache existiert → direkt laden
    if CACHE_PATH.exists():
        try:
            cache = pd.read_csv(CACHE_PATH, index_col=0)
            return cache["p_up"].to_dict()
        except Exception:
            pass

    from .config import TEAMS

    p_up_map = {}

    print("📥 Lade Momentum (p_up) für alle Teams ...")

    for t in TEAMS:
        name = t.name
        code = t.code

        # --- Playoff-Pfade: Durchschnitt der Kandidaten ---
        if name in PLAYOFF_PATHS:
            candidates = PLAYOFF_PATHS[name]
            vals = []
            for c in candidates:
                df_matches = fetch_last_matches(c)
                vals.append(compute_p_up(df_matches))
            p_up_map[code] = sum(vals) / len(vals)
            continue

        # --- Normale Teams ---
        lookup_name = TEAM_NAME_MAP.get(name, None)
        if lookup_name is None:
            print(f"⚠️ Kein Mapping für {name} → p_up=0.50")
            p_up_map[code] = 0.50
            continue

        df_matches = fetch_last_matches(lookup_name)
        p_up_map[code] = compute_p_up(df_matches)

    # Cache speichern
    df_cache = pd.DataFrame.from_dict(p_up_map, orient="index", columns=["p_up"])
    df_cache.to_csv(CACHE_PATH)

    print("✅ Momentum gespeichert:", CACHE_PATH)
    return p_up_map

