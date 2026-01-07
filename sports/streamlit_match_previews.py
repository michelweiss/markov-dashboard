#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pandas as pd
import streamlit as st
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

PREVIEWS_FILE  = DATA_DIR / "fixture_previews.json"
FIXTURES_FILE  = DATA_DIR / "upcoming_fixtures.csv"

st.set_page_config(
    page_title="Premier League p_win – Match Preview",
    layout="wide"
)

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
@st.cache_data
def load_previews():
    with open(PREVIEWS_FILE) as f:
        data = json.load(f)
    return pd.DataFrame(data)

@st.cache_data
def load_pwin_map():
    df = pd.read_csv(DATA_DIR / "pwin_states.csv")
    return df.set_index("state")[["p_win", "p_draw", "samples"]].to_dict("index")

@st.cache_data
def load_market():
    path = DATA_DIR / "market_kalshi.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_fixtures():
    if FIXTURES_FILE.exists():
        return pd.read_csv(FIXTURES_FILE, parse_dates=["date"])
    return pd.DataFrame()

df = load_previews()
fixtures = load_fixtures()
pwin_map = load_pwin_map()
market = load_market()

# split home / away
df_home = df[df.is_home == 1].set_index("team")
df_away = df[df.is_home == 0].set_index("team")

teams = sorted(df_home.index.intersection(df_away.index))

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
st.title("⚽ Premier League – Match Preview (p_win / p_draw)")
st.caption("State v1 = (Form, Home) · zustandsbasiert · erklärbar")

st.markdown("### 📅 Upcoming Fixtures")

if not fixtures.empty:
    fixture_label = fixtures.apply(
        lambda r: f"{r.home_team} vs {r.away_team} ({r.date.date()})",
        axis=1
    )
    selected_fixture = st.selectbox("Select upcoming match", fixture_label.tolist())
    row = fixtures.loc[fixture_label == selected_fixture].iloc[0]
    home_team = row.home_team
    away_team = row.away_team
else:
    st.warning("Keine Upcoming Fixtures gefunden – manueller Modus aktiv.")
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("🏠 Home Team", teams, index=0)
    with col2:
        away_team = st.selectbox("🚗 Away Team", teams, index=1)

# ─────────────────────────────────────────────
# MARKET MATCH
# ─────────────────────────────────────────────
market_row = None
if not market.empty:
    m = market[
        (market.home_team == home_team) &
        (market.away_team == away_team)
    ]
    if not m.empty:
        market_row = m.iloc[0]

# ─────────────────────────────────────────────
# COMPUTE MATCH PREVIEW (CONSISTENT + CONFIDENCE)
# ─────────────────────────────────────────────
p_home = float(df_home.loc[home_team].p_win)

p_draw = (
    float(df_home.loc[home_team].p_draw) +
    float(df_away.loc[away_team].p_draw)
) / 2

p_away = max(0.0, 1.0 - p_home - p_draw)

form_home = int(df_home.loc[home_team].form)
form_away = int(df_away.loc[away_team].form)
rel_form  = form_home - form_away

edge = p_home - p_away
edge_abs = abs(edge)

state_home = f"({rel_form},1)"
state_probs = pwin_map.get(state_home)
samples = state_probs["samples"] if state_probs else 0

if edge_abs >= 0.20 and samples >= 50:
    conf_label = "🟢 High"
elif edge_abs >= 0.10 and samples >= 25:
    conf_label = "🟡 Medium"
else:
    conf_label = "🔴 Low"

# ─────────────────────────────────────────────
# MODEL vs MARKET Δ
# ─────────────────────────────────────────────
if market_row is not None:
    d_home = p_home - float(market_row.p_home_market)
    d_draw = p_draw - float(market_row.p_draw_market)
    d_away = p_away - float(market_row.p_away_market)
else:
    d_home = d_draw = d_away = None

# ─────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────
st.markdown("---")
st.subheader(f"{home_team} vs {away_team}")

st.caption(
    f"Relative Form: **{rel_form:+d}**  "
    f"(Form {home_team} = {form_home}, "
    f"Form {away_team} = {form_away})"
)

st.caption(f"Confidence: **{conf_label}**  (samples = {samples})")

if d_home is not None:
    st.caption(
        f"Market vs Model Δ — "
        f"Home: **{d_home:+.1%}**, "
        f"Draw: **{d_draw:+.1%}**, "
        f"Away: **{d_away:+.1%}**"
    )
else:
    st.caption("Market overlay: kein Eintrag vorhanden")

c1, c2, c3 = st.columns(3)
c1.metric("🏠 Home Win", f"{p_home:.2%}")
c2.metric("🤝 Draw", f"{p_draw:.2%}")
c3.metric("🚗 Away Win", f"{p_away:.2%}")

st.progress(min(edge_abs * 2, 1.0))

st.caption(
    f"""
**Interpretation**  
• {home_team} gewinnt historisch in ähnlichen Situationen in **{p_home:.1%}** der Fälle  
• Unentschieden tritt in **{p_draw:.1%}** der Fälle auf  
• {away_team} gewinnt auswärts in **{p_away:.1%}** der Fälle  
• Edge (Home − Away) = **{edge:+.1%}**
"""
)

st.caption(f"Total probability check: **{(p_home+p_draw+p_away):.1%}**")

# ─────────────────────────────────────────────
# TABLE VIEW
# ─────────────────────────────────────────────
st.markdown("---")
st.subheader("🔍 Alle Teams – State Snapshot")

st.dataframe(
    df.sort_values("p_win", ascending=False)[
        ["team", "is_home", "form", "state", "p_win", "p_draw"]
    ],
    use_container_width=True
)

