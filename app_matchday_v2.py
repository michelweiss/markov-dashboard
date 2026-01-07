#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pandas as pd
import streamlit as st
import unicodedata
import re
import sys
from datetime import date
from economics.ui import render_economics_tab
from pathlib import Path

MARKOV_ROOT = Path(__file__).resolve().parent
if str(MARKOV_ROOT) not in sys.path:
    sys.path.insert(0, str(MARKOV_ROOT))

# --------------------------------------------------
# DEMO MODE
# --------------------------------------------------
DEMO_MODE = True   # ← für GitHub / Kollegen
# DEMO_MODE = False  # ← für dich lokal mit API

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
SPORTS_DIR = ROOT / "sports"


# ─────────────────────────────────────────────
# LEAGUES  
# ─────────────────────────────────────────────
LEAGUES = {
    "Premier League": "epl",
    "LaLiga": "laliga",
    "Serie A": "seriea",
    "Ligue 1": "ligue1",
}


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Probability Dashboard",
    layout="wide"
)

# ─────────────────────────────────────────────
# LOADERS (LEAGUE-AWARE)
# ─────────────────────────────────────────────

@st.cache_data
def load_fixtures(data_dir: Path):
    file = data_dir / "upcoming_fixtures.csv"
    if file.exists():
        df = pd.read_csv(file, parse_dates=["date"])
        df["matchday"] = df["date"].dt.date
        return df
    return pd.DataFrame()


@st.cache_data
def load_previews(data_dir: Path):
    file = data_dir / "fixture_previews.json"
    if file.exists():
        with open(file) as f:
            return pd.DataFrame(json.load(f))
    return pd.DataFrame()


@st.cache_data
def load_pwin_map(data_dir: Path):
    file = data_dir / "pwin_states.csv"
    if file.exists():
        df = pd.read_csv(file)
        return df.set_index("state")[["samples"]].to_dict("index")
    return {}


@st.cache_data
def load_team_matches(data_dir: Path):
    file = data_dir / "team_matches.csv"
    if file.exists():
        return pd.read_csv(file, parse_dates=["date"])
    return pd.DataFrame()


@st.cache_data
def compute_team_strength_from_matches(team_df: pd.DataFrame):
    """
    Team strength = Points per Game (PPG), z-scored
    win=3, draw=1, loss=0
    """
    if team_df.empty:
        return pd.Series(dtype=float)

    if "draw" not in team_df.columns:
        team_df = team_df.copy()
        team_df["draw"] = 0

    points = team_df["win"] * 3 + team_df["draw"]
    ppg = points.groupby(team_df["team"]).mean()

    std = ppg.std()
    if std == 0 or pd.isna(std):
        std = 1.0

    return (ppg - ppg.mean()) / std

@st.cache_data
def load_json(path: Path):
    with open(path) as f:
        return json.load(f)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def norm_team(x: str) -> str:
    if not isinstance(x, str):
        return ""
    x = unicodedata.normalize("NFKC", x)
    return " ".join(x.split())

def traffic_light(p: float) -> str:
    if p >= 0.55:
        return "🟢"
    if p >= 0.40:
        return "🟡"
    return "🔴"

def confidence_light(conf: float) -> str:
    """
    Economics confidence traffic light
    🟢 = high regime certainty
    🟡 = moderate certainty
    🔴 = low certainty / open outcome
    """
    if conf >= 0.70:
        return "🟢"
    if conf >= 0.50:
        return "🟡"
    return "🔴"


def build_matchday_table(day):

    fx = fixtures[fixtures.matchday == day].copy()
    rows = []

    for _, r in fx.iterrows():

        home = r.home_team
        away = r.away_team
    
        home_n = norm_team(home)
        away_n = norm_team(away)

        
        ph = previews[(previews.team_n == home_n) & (previews.is_home == 1)].iloc[0]
        pa = previews[(previews.team_n == away_n) & (previews.is_home == 0)].iloc[0]

        # base probabilities
        p_home = ph.p_win
        p_draw = (ph.p_draw + pa.p_draw) / 2
        p_away = 1 - p_home - p_draw

        # strength adjustment
        alpha = 0.08
        s_home = team_strength.get(home_n, 0.0)
        s_away = team_strength.get(away_n, 0.0)

        adj = alpha * (s_home - s_away)

        p_home += adj
        p_away -= adj

        # floor + renormalize
        p_home = max(0.01, p_home)
        p_draw = max(0.01, p_draw)
        p_away = max(0.01, p_away)

        Z = p_home + p_draw + p_away
        p_home /= Z
        p_draw /= Z
        p_away /= Z

        # diagnostics
        rel_form = int(ph.form - pa.form)
        
        state = f"({rel_form},1)"

        rows.append({
            "Home Team": home,
            "Away Team": away,
            "Home Win": f"{traffic_light(p_home)} {round(p_home*100)}%",
            "Draw":     f"{traffic_light(p_draw*100/100)} {round(p_draw*100)}%",
            "Away Win": f"{traffic_light(p_away)} {round(p_away*100)}%",
        })
  
    return pd.DataFrame(rows)

def render_financial_risk():

    DATA_DIR = MARKOV_ROOT / "financial" / "data"

    files = {
        "D": [
            DATA_DIR / "equity_probabilities_daily.json",
            DATA_DIR / "credit_probabilities_daily.json",
            DATA_DIR / "vix_probabilities_daily.json",
        ],
        "W": [
            DATA_DIR / "equity_probabilities_weekly.json",
            DATA_DIR / "credit_probabilities_weekly.json",
            DATA_DIR / "vix_probabilities_weekly.json",
        ],
        "M": [
            DATA_DIR / "equity_probabilities_monthly.json",
            DATA_DIR / "credit_probabilities_monthly.json",
            DATA_DIR / "vix_probabilities_monthly.json",
        ],
    }

    # ── load + merge indices per freq
    data = {"D": {}, "W": {}, "M": {}}

    for freq in ("D", "W", "M"):
        for p in files[freq]:
            if not p.exists():
                st.warning(f"Missing {p.name}")
                return
            js = load_json(p)
            idx = js.get("indices", {})
            if isinstance(idx, dict):
                data[freq].update(idx)

    # ── build rows using D as master key set
    rows = []
    for key, info in data["D"].items():
        # fetch p_up for each horizon (may be missing)
        p_d = data["D"].get(key, {}).get("p_up", None)
        p_w = data["W"].get(key, {}).get("p_up", None)
        p_m = data["M"].get(key, {}).get("p_up", None)

        # Credit semantics: p_up = Stress ↑ (Risk-Off) → invert for display (Risk-On)
        is_credit = "credit" in key.lower()

        if is_credit:
            p_d = (1 - p_d) if (p_d is not None and not pd.isna(p_d)) else p_d
            p_w = (1 - p_w) if (p_w is not None and not pd.isna(p_w)) else p_w
            p_m = (1 - p_m) if (p_m is not None and not pd.isna(p_m)) else p_m

        rows.append({
            "Region": info.get("region", ""),
            "Index": info.get("label", key),
            "D": p_d,
            "W": p_w,
            "M": p_m,
        })

    df = pd.DataFrame(rows)

    def fmt(p):
        if p is None or pd.isna(p):
            return "–"
        pct = int(round(float(p) * 100))
        if p >= 0.65:
            icon = "🟢"
        elif p >= 0.50:
            icon = "🟡"
        else:
            icon = "🔴"
        return f"{icon} {pct}%"

    for c in ["D", "W", "M"]:
        df[c] = df[c].apply(fmt)

    # Optional: stabile Sortierung
    REGION_ORDER = ["USA", "Europe", "Switzerland", "Japan"]
    df["Region"] = pd.Categorical(df["Region"], REGION_ORDER)
    df = df.sort_values(["Region", "Index"])

    REGION_FLAG = {
        "USA": "🇺🇸",
        "Europe": "🇪🇺",
        "Switzerland": "🇨🇭",
        "Japan": "🇯🇵",
    }
    df["Region"] = df["Region"].apply(lambda r: f"{REGION_FLAG.get(r, '')} {r}")

    st.subheader("📊 Financial · Risk Regime (Rolling Probabilities)")
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.caption(
        "Rolling Markov probabilities · "
        "Daily = 1d · Weekly = 5d · Monthly = 21d · "
        "Credit is displayed as Risk-On (inverted from stress)."
    )



# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
st.title("📊 Probability Research Dashboard")

tab_sports, tab_economics, tab_financial, tab_climate, tab_about = st.tabs(
    ["Sports", "Economics", "Financial", "Climate", "About"]
)

# ─────────────────────────────────────────────
# SPORTS TAB
# ─────────────────────────────────────────────
with tab_sports:

    st.subheader("⚽ Football")

    # ------------------------------
    # League selector (LOCAL)
    # ------------------------------
    league_name = st.radio(
        "League",
        ["Premier League", "LaLiga", "Serie A", "Ligue 1"],
        horizontal=True
    )

    LEAGUE = LEAGUES[league_name]
    DATA_DIR = SPORTS_DIR / "data" / LEAGUE

    # ------------------------------
    # Load league-specific data
    # ------------------------------
    fixtures     = load_fixtures(DATA_DIR)
    previews     = load_previews(DATA_DIR)
    pwin_map     = load_pwin_map(DATA_DIR)
    team_matches = load_team_matches(DATA_DIR)

    # ------------------------------
    # Normalize & derived data (MUST be here)
    # ------------------------------
    if not previews.empty:
        previews["team_n"] = previews["team"].apply(norm_team)

    if not fixtures.empty:
        fixtures["home_n"] = fixtures["home_team"].apply(norm_team)
        fixtures["away_n"] = fixtures["away_team"].apply(norm_team)


    team_strength = compute_team_strength_from_matches(team_matches)
    if isinstance(team_strength, pd.Series) and not team_strength.empty:
        team_strength = team_strength.copy()
        team_strength.index = team_strength.index.map(norm_team)
        team_strength = team_strength.groupby(level=0).mean()

    st.markdown(f"### {league_name} – Matchdays")

    if fixtures.empty:
        st.warning("No fixtures available.")
    else:
        # -------------------------------------
        # MATCHDAY OPTIONS (past + future)
        # -------------------------------------
        fixtures["matchday"] = pd.to_datetime(fixtures["matchday"]).dt.date
        all_days = sorted(fixtures.matchday.unique())
    
        today = date.today()
    
        past_days   = [d for d in all_days if d < today][-3:]
        future_days = [d for d in all_days if d >= today]
    
        day_options = past_days + future_days
    
        # Default: next / current matchday
        default_day = future_days[0] if future_days else all_days[-1]
    
        # -------------------------------------
        # MATCHDAY SELECTOR (selectable!)
        # -------------------------------------
        active_day = st.radio(
            "Matchday",
            day_options,
            index=day_options.index(default_day),
            horizontal=True
        )
    
        st.markdown("---")
    
        # -------------------------------------
        # TABLE FOR SELECTED MATCHDAY
        # -------------------------------------
        df_day = build_matchday_table(active_day)
    
        st.markdown(f"### Matchday {active_day}")
    
        st.dataframe(
            df_day,
            use_container_width=True
        )
        

                
# ─────────────────────────────────────────────
# ECONOMICS TAB
# ─────────────────────────────────────────────
with tab_economics:
    render_economics_tab()

# ─────────────────────────────────────────────
# FINANCIAL TAB
# ─────────────────────────────────────────────
with tab_financial:
    render_financial_risk()

# ─────────────────────────────────────────────
# CLIMATE TAB (PLACEHOLDER)
# ─────────────────────────────────────────────
with tab_climate:
    st.subheader("Climate / ESG (coming later)")
    st.info("Climate risk, weather events, ESG probabilities.")

# ─────────────────────────────────────────────
# ABOUT
# ─────────────────────────────────────────────
with tab_about:
    st.markdown("""
    **Probability Research Dashboard**

    • State-based probabilities  
    • Explainable confidence  
    • Model vs Market overlays  
    • Sports, Macro & Equity unified  

    Built for research – not betting.
    """)

