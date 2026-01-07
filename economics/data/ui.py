#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"


@st.cache_data
def load_macro_events():
    file = DATA_DIR / "macro_events.csv"
    if file.exists():
        return pd.read_csv(file, parse_dates=["date"])
    return pd.DataFrame()


@st.cache_data
def load_event_states():
    file = DATA_DIR / "event_states.csv"
    if file.exists():
        return pd.read_csv(file, parse_dates=["date"])
    return pd.DataFrame()


@st.cache_data
def load_pwin_events():
    file = DATA_DIR / "pwin_events.csv"
    if file.exists():
        return pd.read_csv(file)
    return pd.DataFrame()
    

@st.cache_data
def load_pwin_nfp():
    f = DATA_DIR / "pwin_nfp.csv"
    if f.exists():
        return pd.read_csv(f)
    return pd.DataFrame()
    

@st.cache_data
def load_pwin_cpi():
    f = DATA_DIR / "pwin_cpi.csv"
    if f.exists():
        return pd.read_csv(f)
    return pd.DataFrame()


@st.cache_data
def load_pwin_fomc():
    f = DATA_DIR / "pwin_fomc.csv"
    if f.exists():
        return pd.read_csv(f)
    return pd.DataFrame()


@st.cache_data
def load_pwin_gdp():
    f = DATA_DIR / "pwin_gdp.csv"
    if f.exists():
        return pd.read_csv(f)
    return pd.DataFrame()
    

@st.cache_data
def load_pwin_ecb():
    f = DATA_DIR / "pwin_ecb.csv"
    if f.exists():
        return pd.read_csv(f)
    return pd.DataFrame()


@st.cache_data
def load_pwin_eu_cpi():
    f = DATA_DIR / "pwin_eu_cpi.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_pwin_snb():
    f = DATA_DIR / "pwin_snb.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


def render_economics_tab():

    st.subheader("📊 Macro Economics")

    events = load_macro_events()
    states = load_event_states()
    pwin   = load_pwin_events()

    # ------------------------------
    # CPI SUMMARY 
    # ------------------------------
    cpi_summary = {}

    pwin_cpi = load_pwin_cpi()
    states_cpi = pd.read_csv(DATA_DIR / "event_states_cpi.csv")
    
    if not pwin_cpi.empty and not states_cpi.empty:
    
        latest_state = states_cpi.sort_values("date").iloc[-1]["state"]
        g = pwin_cpi[pwin_cpi.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
    
            cpi_summary = {
                "label": f"{top.outcome.title()} ({top.p_shrunk:.0%})",
                "probs": g.set_index("outcome")["p_shrunk"].to_dict()
            }

    if events.empty:
        st.warning("No macro events available.")
        return

    today = date.today()
    events["event_day"] = events["date"].dt.date

    upcoming = events[events.event_day >= today]
    upcoming = (
        upcoming
        .sort_values("date")
        .groupby("event", as_index=False)
        .first()
    )


    # ------------------------------
    # NFP SUMMARY (REAL, SAFE)
    # ------------------------------
    nfp_summary = {}

    pwin_nfp = load_pwin_nfp()
    states_nfp = pd.read_csv(DATA_DIR / "event_states_nfp.csv")
    
    if not pwin_nfp.empty and not states_nfp.empty:
    
        latest_state = states_nfp.sort_values("date").iloc[-1]["state"]
        g = pwin_nfp[pwin_nfp.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
    
            nfp_summary = {
                "label": f"{top.outcome.title()} ({top.p_shrunk:.0%})",
                "probs": g.set_index("outcome")["p_shrunk"].to_dict()
            }


    # ------------------------------
    # FOMC SUMMARY (3-class Markov)
    # ------------------------------
    fomc_summary = {}
    
    pwin_fomc = load_pwin_fomc()
    states_fomc = pd.read_csv(DATA_DIR / "event_states_fomc.csv")
    
    if not pwin_fomc.empty and not states_fomc.empty:
    
        latest_state = states_fomc.sort_values("date").iloc[-1]["state"]
    
        g = pwin_fomc[pwin_fomc.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
    
            fomc_summary = {
                "label": f"{top.outcome} ({top.p_shrunk:.0%})",
                "probs": g.set_index("outcome")["p_shrunk"].to_dict()
            }

    # ------------------------------
    # GDP SUMMARY (Markov bins)
    # ------------------------------
    gdp_summary = {}
    
    pwin_gdp = load_pwin_gdp()
    states_gdp = pd.read_csv(DATA_DIR / "event_states_gdp.csv")
    
    if not pwin_gdp.empty and not states_gdp.empty:
    
        latest_state = states_gdp.sort_values("date").iloc[-1]["state"]
    
        g = pwin_gdp[pwin_gdp.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
    
            gdp_summary = {
                "label": f"{top.outcome.title()} ({top.p_shrunk:.0%})",
                "probs": g.set_index("outcome")["p_shrunk"].to_dict()
            }

    # ------------------------------
    # ECB SUMMARY (3-class Markov)
    # ------------------------------
    ecb_summary = {}
    
    pwin_ecb = load_pwin_ecb()
    states_ecb = pd.read_csv(DATA_DIR / "event_states_ecb.csv")
    
    if not pwin_ecb.empty and not states_ecb.empty:
    
        latest_state = (
            states_ecb
            .sort_values("date")
            .iloc[-1]["state"]
        )
    
        g = pwin_ecb[pwin_ecb.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
    
            ecb_summary = {
                "label": f"{top.outcome} ({top.p_shrunk:.0%})",
                "probs": g.set_index("outcome")["p_shrunk"].to_dict()
            }

    # ------------------------------
    # EU CPI SUMMARY
    # ------------------------------
    eu_cpi_summary = {}
    
    pwin_eu_cpi = load_pwin_eu_cpi()
    states_eu_cpi = pd.read_csv(DATA_DIR / "event_states_eu_cpi.csv")
    
    if not pwin_eu_cpi.empty and not states_eu_cpi.empty:
    
        latest_state = (
            states_eu_cpi
            .sort_values("date")
            .iloc[-1]["state"]
        )
    
        g = pwin_eu_cpi[pwin_eu_cpi.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
    
            eu_cpi_summary = {
                "label": f"{top.outcome.title()} ({top.p_shrunk:.0%})",
                "probs": g.set_index("outcome")["p_shrunk"].to_dict()
            }

    # ------------------------------
    # EU GDP SUMMARY (Markov bins)
    # ------------------------------
    eu_gdp_summary = {}
    
    pwin_eu_gdp = pd.read_csv(DATA_DIR / "pwin_eu_gdp.csv")
    states_eu_gdp = pd.read_csv(DATA_DIR / "event_states_eu_gdp.csv")
    
    if not pwin_eu_gdp.empty and not states_eu_gdp.empty:
    
        latest_state = (
            states_eu_gdp
            .sort_values("date")
            .iloc[-1]["state"]
        )
    
        g = pwin_eu_gdp[pwin_eu_gdp.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
    
            eu_gdp_summary = {
                "label": f"{top.outcome.title()} ({top.p_shrunk:.0%})",
                "probs": g.set_index("outcome")["p_shrunk"].to_dict()
            }


    # ------------------------------
    # UPCOMING EVENTS (Calendar)
    # ------------------------------
    st.markdown("### 📅 Upcoming Macro Events")

    upcoming["Region"] = upcoming["country"].map({
        "US": "🇺🇸 USA",
        "EU": "🇪🇺 Europe",
        "CH": "🇨🇭 Switzerland",
    }).fillna(upcoming["country"])

    table = upcoming.copy()

    # default empty columns
    table["Conf"] = "—"
    
    if cpi_summary:
        cpi_dates = table[
            (table["event"] == "US CPI") &
            (table["date"].dt.date >= today)
        ].sort_values("date")
    
        if not cpi_dates.empty:
            d = cpi_dates.iloc[0]["date"]
            mask = (table["event"] == "US CPI") & (table["date"] == d)
        else:
            mask = table["event"] == "US CPI"
    
        table.loc[mask, "Conf"] = cpi_summary["label"]
    
        
    if nfp_summary:
        nfp_dates = table[
            (table["event"] == "US NFP") &
            (table["date"].dt.date >= today)
        ].sort_values("date")
    
        if not nfp_dates.empty:
            d = nfp_dates.iloc[0]["date"]
            mask = (table["event"] == "US NFP") & (table["date"] == d)
        else:
            mask = table["event"] == "US NFP"
    
        table.loc[mask, "Conf"] = nfp_summary["label"]
    
                 
    if gdp_summary:
        gdp_dates = table[
            table["event"].str.contains("US GDP", na=False)
        ].sort_values("date")
    
        if not gdp_dates.empty:
            d = gdp_dates.iloc[0]["date"]
            mask = table["event"].str.contains("US GDP", na=False) & (table["date"] == d)
        else:
            mask = table["event"].str.contains("US GDP", na=False)
    
        table.loc[mask, "Conf"] = gdp_summary["label"]
    


    if fomc_summary:
        fomc_dates = table[
            (table["event"] == "FOMC") &
            (table["date"].dt.date >= today)
        ].sort_values("date")
    
        if not fomc_dates.empty:
            d = fomc_dates.iloc[0]["date"]
            mask = (table["event"] == "FOMC") & (table["date"] == d)
        else:
            mask = table["event"] == "FOMC"
    
        table.loc[mask, "Conf"] = fomc_summary["label"]


    if ecb_summary:
        ecb_dates = table[
            (table["event"] == "ECB") &
            (table["date"].dt.date >= today)
        ].sort_values("date")
    
        if not ecb_dates.empty:
            d = ecb_dates.iloc[0]["date"]
            mask = (table["event"] == "ECB") & (table["date"] == d)
        else:
            mask = table["event"] == "ECB"
    
        table.loc[mask, "Conf"] = ecb_summary["label"]

    if eu_cpi_summary:
        mask = table["event"] == "EU CPI"
        table.loc[mask, "Conf"] = eu_cpi_summary["label"]

    if eu_gdp_summary:
        mask = table["event"] == "EU GDP"
        table.loc[mask, "Conf"] = eu_gdp_summary["label"]


    table = table.sort_values("date").reset_index(drop=True)

    st.dataframe(
        table[
            ["date", "Region", "event", "Conf"]   # nur noch diese
        ],
        use_container_width=True
    )


