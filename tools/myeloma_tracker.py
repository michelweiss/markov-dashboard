#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# 🩸 Myelom-Dashboard (Streamlit)
# ------------------------------------------------------------
# Funktionen:
# • Automatisches Einlesen der Laborwerte_Myelom_Template.csv
# • Auswahl & Visualisierung wichtiger Marker
# • Kommentare zu Verlauf (prozentuale Änderung)
# • Gesundheits-Hinweise (Hydration, Ernährung, Schlaf etc.)
# ------------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os

# ============================================================
# 1️⃣  CSV EINLESEN
# ============================================================
# 💾 Passe den Pfad zu deinem Mac an:
FILE_PATH = "/Users/michelweiss/Documents/Python_for_Finance/CSV/Laborwerte_Myelom_Template.csv"

st.set_page_config(page_title="Myelom Dashboard", layout="wide")

st.title("🩸 Myelom Dashboard")
st.caption("Verlaufsanalyse & Selbstmanagement-Hinweise")

if not os.path.exists(FILE_PATH):
    st.error(f"CSV-Datei **{FILE_PATH}** nicht gefunden.\n\n"
             "Bitte prüfe den Pfad oder exportiere die Datei erneut aus Numbers.")
    st.stop()

# CSV laden
df = pd.read_csv(FILE_PATH)

# Datumsspalte erkennen und konvertieren
if "Datum" in df.columns:
    df["Datum_parsed"] = pd.to_datetime(df["Datum"], errors="coerce")
else:
    df["Datum_parsed"] = pd.NaT

# Zahlkonvertierung (Komma → Punkt)
def to_num(x):
    if pd.isna(x):
        return np.nan
    x = str(x).replace(",", ".").strip()
    try:
        return float(x)
    except ValueError:
        return np.nan

for c in df.columns:
    if c not in ["Datum", "Datum_parsed", "Zyklus", "Label"]:
        df[c] = df[c].apply(to_num)

# ============================================================
# 2️⃣  UI – AUSWAHL DER MARKER
# ============================================================
st.sidebar.header("⚙️ Optionen")

default_cols = [
    "Kappa frei (mg/L)",
    "Kappa/Lambda Ratio",
    "M-Protein qn (S) (g/L)",
]
available_cols = [c for c in default_cols if c in df.columns]

selected_cols = st.sidebar.multiselect(
    "Wähle Laborwerte zur Anzeige",
    options=df.columns,
    default=available_cols,
)

# Zeitbereich
min_date, max_date = df["Datum_parsed"].min(), df["Datum_parsed"].max()
if pd.isna(min_date) or pd.isna(max_date):
    st.warning("Keine gültigen Datumsangaben gefunden.")
    st.stop()

date_range = st.sidebar.slider(
    "Zeitraum",
    min_value=min_date.to_pydatetime(),
    max_value=max_date.to_pydatetime(),
    value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
    format="DD.MM.YYYY"
)

mask = (df["Datum_parsed"] >= date_range[0]) & (df["Datum_parsed"] <= date_range[1])
df_filtered = df.loc[mask]

# ============================================================
# 3️⃣  GRAFISCHE DARSTELLUNG
# ============================================================
if not selected_cols:
    st.warning("Bitte mindestens einen Marker auswählen.")
else:
    fig, ax = plt.subplots(figsize=(10, 5))
    for col in selected_cols:
        if col in df_filtered.columns and df_filtered[col].notna().any():
            ax.plot(
                df_filtered["Datum_parsed"],
                df_filtered[col],
                marker="o",
                label=col
            )

    ax.set_title("📊 Verlauf ausgewählter Laborwerte", fontsize=14)
    ax.set_xlabel("Datum")
    ax.set_ylabel("Wert")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.5)
    st.pyplot(fig)

# ============================================================
# 4️⃣  VERLÄUFE UND KOMMENTARE
# ============================================================
st.subheader("📈 Veränderungen & Bewertung")

def pct_change(col):
    s = df_filtered[col].dropna()
    if len(s) < 2:
        return np.nan
    first, last = s.iloc[0], s.iloc[-1]
    if first == 0 or pd.isna(first) or pd.isna(last):
        return np.nan
    return (last - first) / abs(first) * 100

comments = []
for col in selected_cols:
    pc = pct_change(col)
    if np.isnan(pc):
        continue
    arrow = "⬇️" if pc < 0 else "⬆️"
    lower_better = any(x in col for x in ["Kappa", "M-Protein", "CRP", "LDH", "Kreatinin"])
    good = (pc < 0) if lower_better else (pc > 0)
    tag = "✅ positiv" if good else "⚠️ beobachten"
    comments.append(f"{col}: {arrow} {pc:.1f}% ({tag})")

if comments:
    for c in comments:
        st.write("•", c)
else:
    st.info("Noch nicht genügend Daten für Trendanalyse.")

# ============================================================
# 5️⃣  ALLGEMEINE EMPFEHLUNGEN
# ============================================================
st.subheader("🩺 Praktische Hinweise")

st.markdown("""
- 💧 **Hydration:** 2–2.5 L/Tag (wasser/tee-basiert) – unterstützt Niere & Clearance freier Leichtketten  
- 🚶 **Bewegung:** 20–30 min moderates Gehen oder Radfahren – gut für Knochen, Entzündung & Stoffwechsel  
- 💤 **Schlaf:** 7–8 h pro Nacht; regelmäßiger Rhythmus hält CRP & LDH niedrig  
- 🍽️ **Ernährung:** ausgewogen, keine Crash-Diäten; Eiweißzufuhr normal  
- 🍷 **Alkohol:** sparsam, nicht an Labortagen; Nikotin vermeiden  
- 🤧 **Infekte:** bei CRP-Anstieg Erholung priorisieren – Laborwerte erst nach Genesung interpretieren  
""")

# ============================================================
# 6️⃣  DOWNLOAD / SPEICHERN
# ============================================================
st.sidebar.download_button(
    "📤 CSV herunterladen",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="Laborwerte_Myelom_Aktuell.csv",
    mime="text/csv"
)

st.sidebar.caption("Version 1.0 – Michel Weiss · GPT-5 Integration")

