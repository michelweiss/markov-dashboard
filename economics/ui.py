#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import streamlit as st
import re
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
    

@st.cache_data
def load_pwin_ch_cpi():
    f = DATA_DIR / "pwin_ch_cpi.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


@st.cache_data
def load_pwin_ch_gdp():
    f = DATA_DIR / "pwin_ch_gdp.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


def confidence_light(conf: float) -> str:
    # Economics = regime certainty (NOT direction)
    if conf >= 0.70:
        return "🟢"
    if conf >= 0.50:
        return "🟡"
    return "🔴"

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

    now = pd.Timestamp.today()

    upcoming = events[
        (events["date"].dt.year == now.year) &
        (events["date"].dt.month == now.month)
    ]
    
    upcoming = (
        upcoming
        .sort_values("date")
        .groupby(["event", "country"], as_index=False)
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
    # SNB SUMMARY (3-class Markov)
    # ------------------------------
    snb_summary = {}
    
    pwin_snb = load_pwin_snb()
    states_snb = pd.read_csv(DATA_DIR / "event_states_snb.csv")
    
    if not pwin_snb.empty and not states_snb.empty:
    
        latest_state = states_snb.sort_values("date").iloc[-1]["state"]
        g = pwin_snb[pwin_snb.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
            snb_summary = {
                "label": f"{top.outcome} ({top.p_shrunk:.0%})"
            }

    # ------------------------------
    # CH CPI SUMMARY
    # ------------------------------
    ch_cpi_summary = {}
    
    pwin_ch_cpi = load_pwin_ch_cpi()
    states_ch_cpi = pd.read_csv(DATA_DIR / "event_states_ch_cpi.csv")
    
    if not pwin_ch_cpi.empty and not states_ch_cpi.empty:
    
        latest_state = (
            states_ch_cpi
            .sort_values("date")
            .iloc[-1]["state"]
        )
    
        g = pwin_ch_cpi[pwin_ch_cpi.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
    
            ch_cpi_summary = {
                "label": f"{top.outcome.title()} ({top.p_shrunk:.0%})",
                "probs": g.set_index("outcome")["p_shrunk"].to_dict()
            }


    # ------------------------------
    # CH GDP SUMMARY (Markov bins)
    # ------------------------------
    ch_gdp_summary = {}
    
    pwin_ch_gdp = load_pwin_ch_gdp()
    states_ch_gdp = pd.read_csv(DATA_DIR / "event_states_ch_gdp.csv")
    
    if not pwin_ch_gdp.empty and not states_ch_gdp.empty:
    
        latest_state = (
            states_ch_gdp
            .sort_values("date")
            .iloc[-1]["state"]
        )
    
        g = pwin_ch_gdp[pwin_ch_gdp.state == latest_state]
    
        if not g.empty:
            top = g.sort_values("p_shrunk", ascending=False).iloc[0]
    
            ch_gdp_summary = {
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
    
    # US CPI
    if cpi_summary:
        table.loc[table["event"] == "US CPI", "Conf"] = cpi_summary["label"]
    
    # US NFP
    if nfp_summary:
        table.loc[table["event"] == "US NFP", "Conf"] = nfp_summary["label"]
    
    # US GDP
    if gdp_summary:
        table.loc[table["event"].str.contains("US GDP", na=False), "Conf"] = gdp_summary["label"]
    
    # FOMC
    if fomc_summary:
        table.loc[table["event"] == "FOMC", "Conf"] = fomc_summary["label"]
    
    # ECB
    if ecb_summary:
        table.loc[table["event"] == "ECB", "Conf"] = ecb_summary["label"]
    
    # EU CPI
    if eu_cpi_summary:
        table.loc[table["event"] == "EU CPI", "Conf"] = eu_cpi_summary["label"]
    
    # EU GDP
    if eu_gdp_summary:
        table.loc[table["event"] == "EU GDP", "Conf"] = eu_gdp_summary["label"]
    
    # SNB
    if snb_summary:
        table.loc[table["event"] == "SNB", "Conf"] = snb_summary["label"]
    
    # CH CPI
    if ch_cpi_summary:
        table.loc[table["event"] == "CH CPI", "Conf"] = ch_cpi_summary["label"]
    
    # CH GDP
    if ch_gdp_summary:
        table.loc[table["event"] == "CH GDP", "Conf"] = ch_gdp_summary["label"]


    # ─────────────────────────────────────────────
    # Confidence → Ampel (Mathematica-style: last column)
    # ─────────────────────────────────────────────
    def extract_conf_pct(x):
        try:
            m = re.search(r"(\d+)%", str(x))
            return float(m.group(1)) / 100 if m else None
        except Exception:
            return None
    
    table = table.sort_values("date").reset_index(drop=True)
    
    table["_conf_pct"] = table["Conf"].apply(extract_conf_pct)
    table[""] = table["_conf_pct"].apply(
        lambda x: confidence_light(x) if x is not None else "–"
    )
    table = table.drop(columns=["_conf_pct"])
    
    st.dataframe(
        table[
            ["date", "Region", "event", "Conf", ""]   # Ampel ganz rechts
        ],
        use_container_width=True
    )
    
    st.caption(
        "🟢 = hoher Regime-Konsens · 🟡 = moderat · 🔴 = unsicher | "
        "Percent = model confidence (not impact)"
    )



