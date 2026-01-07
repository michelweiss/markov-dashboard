#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import pandas as pd
import requests
import streamlit as st
from datetime import datetime
from eod import EodHistoricalData
from markov_core_v1 import preprocess_prices
import altair as alt

# ----------------------------------------------------------------
# Hilfsfunktion: EOD-JSON → DataFrame (inkl. Open, High, Low, Close, Volume)
# ----------------------------------------------------------------
def json_to_df(js):
    if not isinstance(js, list) or not js:
        return pd.DataFrame()
    df = pd.DataFrame(js)
    required_cols = ("date", "open", "high", "low", "close", "volume")
    if not all(c in df.columns for c in required_cols):
        return pd.DataFrame()
    df = df[["date", "open", "high", "low", "close", "volume"]].rename(
        columns={
            "date":   "Date",
            "open":   "Open",
            "high":   "High",
            "low":    "Low",
            "close":  "Close",
            "volume": "Volume",
        }
    )
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")

# ----------------------------------------------------------------
# API-Key laden (expanduser) – fester Pfad
# ----------------------------------------------------------------
def load_api_key():
    default_path = os.path.expanduser("~/documents/python_for_finance/api_token.txt")
    try:
        return open(default_path).read().strip()
    except FileNotFoundError:
        st.error(f"API-Key nicht gefunden unter {default_path}")
        return None

# --- Streamlit UI ---
st.title("Stock-Analyse mit täglichen EOD-Daten und Indikatoren")

# Sidebar-Einstellungen
st.sidebar.header("Einstellungen")
ticker_input = st.sidebar.text_input("Ticker (z.B. AAPL)", value="AAPL")
start_date   = st.sidebar.date_input("Start-Datum", value=datetime(2024, 6, 1))
end_date     = st.sidebar.date_input("End-Datum", value=datetime.now())

if st.sidebar.button("Daten laden & analysieren"):
    API_KEY = load_api_key()
    if not API_KEY:
        st.stop()

    # EOD-Client initialisieren
    eod = EodHistoricalData(API_KEY)
    symbol = ticker_input.upper()

    # ----------------------------------------------------------------
    # Split-Adjusted-Daten abrufen
    # ----------------------------------------------------------------
    raw = eod.get_instrument_ta(
        symbol,
        function="splitadjusted",
        agg_period="d",
        from_=start_date.strftime("%Y-%m-%d"),
        to=end_date.strftime("%Y-%m-%d")
    )

    # JSON → DataFrame
    df_raw = json_to_df(raw)
    if df_raw.empty:
        st.warning("Keine Preisdaten verfügbar.")
        st.stop()

    # ----------------------------------------------------------------
    # Preprocess nur auf Close/Volume für tägliche Basis
    # ----------------------------------------------------------------
    df_daily_cv = df_raw[["Close", "Volume"]].copy()
    df_pre = preprocess_prices(df_daily_cv, "daily", None)
    if df_pre.empty:
        st.warning("Keine Preisdaten nach Preprocessing.")
        st.stop()

    # ----------------------------------------------------------------
    # EMAs und Simple-Indikatoren auf df_pre berechnen
    # ----------------------------------------------------------------
    df_pre["EMA_10"] = df_pre["Close"].ewm(span=10, adjust=False).mean()
    df_pre["EMA_21"] = df_pre["Close"].ewm(span=21, adjust=False).mean()
    df_pre["EMA_50"] = df_pre["Close"].ewm(span=50, adjust=False).mean()
    df_pre.dropna(subset=["EMA_10", "EMA_21", "EMA_50"], inplace=True)

    df_pre["Above_EMAs"] = (
        (df_pre["Close"] > df_pre["EMA_10"])
        & (df_pre["Close"] > df_pre["EMA_21"])
        & (df_pre["Close"] > df_pre["EMA_50"])
    )
    df_pre["Low_Volume"] = df_pre["Volume"] < df_pre["Volume"].rolling(window=30).min().shift(1)

    # ----------------------------------------------------------------
    # Für Heavy_Sell, NRIB, Prior_Upmove: Open/High/Low aus df_raw synchronisieren
    # ----------------------------------------------------------------
    df_oh = df_raw.loc[df_pre.index].copy()
    df_oh["Heavy_Sell"] = (
        (df_oh["Close"] < df_oh["Open"])
        & (df_oh["Volume"] > df_oh["Volume"].rolling(window=20).mean())
    )
    df_oh["NRIB"] = (
        (df_oh["High"] - df_oh["Low"])
        < (df_oh["High"].rolling(window=5).max() - df_oh["Low"].rolling(window=5).min()) * 0.3
    )
    df_oh["Prior_Upmove"] = df_oh["Close"] > df_oh["Close"].shift(20) * 1.2

    # ----------------------------------------------------------------
    # Alle Indikatoren zusammenführen
    # ----------------------------------------------------------------
    df_final = df_pre.join(
        df_oh[["Open", "High", "Low", "Heavy_Sell", "NRIB", "Prior_Upmove"]],
        how="left"
    )

    # ----------------------------------------------------------------
    # Anzeige von Kerndaten
    # ----------------------------------------------------------------
    st.subheader(f"Daten für {ticker_input.upper()} (splitadjusted) von {start_date} bis {end_date}")
    st.write(f"Anzahl Handelsdaten insgesamt: {len(df_final)}")
    st.dataframe(df_final.tail(10)[[
        "Close", "Volume", "EMA_10", "EMA_21", "EMA_50",
        "Above_EMAs", "Low_Volume", "Heavy_Sell", "NRIB", "Prior_Upmove"
    ]])

    # ----------------------------------------------------------------
    # Chart: Kurs und EMAs
    # ----------------------------------------------------------------
    st.subheader("Kurs und EMAs")
    df_plot = df_final[["Close", "EMA_10", "EMA_21", "EMA_50"]].reset_index()
    ema_chart = alt.Chart(df_plot).transform_fold(
        ["Close", "EMA_10", "EMA_21", "EMA_50"],
        as_=["Indikator", "Wert"]
    ).mark_line().encode(
        x="Date:T",
        y="Wert:Q",
        color="Indikator:N"
    ).properties(width=700, height=400)
    st.altair_chart(ema_chart, use_container_width=True)

    # ----------------------------------------------------------------
    # Chart: Volumen mit Low-Volume-Markierung
    # ----------------------------------------------------------------
    st.subheader("Volumen mit Low-Volume-Markierung")
    vol_df = df_final.reset_index()
    vol_chart = alt.Chart(vol_df).mark_bar().encode(
        x="Date:T",
        y="Volume:Q",
        color=alt.condition(
            alt.datum.Low_Volume == True,
            alt.value("firebrick"),
            alt.value("steelblue")
        )
    ).properties(width=700, height=200)
    st.altair_chart(vol_chart, use_container_width=True)

    # ----------------------------------------------------------------
    # Tabellen für Spezial-Indikatoren
    # ----------------------------------------------------------------
    st.subheader("Tage mit extrem niedrigem Volumen (Low_Volume == True)")
    if not df_final[df_final["Low_Volume"]].empty:
        st.dataframe(df_final[df_final["Low_Volume"]][["Close", "Volume", "Low_Volume"]].tail(5))
    else:
        st.write("Keine Low-Volume-Tage gefunden.")

    st.subheader("Tage mit Heavy Selling (Heavy_Sell == True)")
    if not df_final[df_final["Heavy_Sell"]].empty:
        st.dataframe(df_final[df_final["Heavy_Sell"]][["Close", "Open", "Volume", "Heavy_Sell"]].tail(5))
    else:
        st.write("Keine Heavy-Selling-Tage gefunden.")

    st.subheader("Tage mit NRIB == True")
    if not df_final[df_final["NRIB"]].empty:
        st.dataframe(df_final[df_final["NRIB"]][["Close", "High", "Low", "NRIB"]].tail(5))
    else:
        st.write("Keine NRIB-Tage gefunden.")

    st.subheader("Tage mit starkem Vorwärtsmove (Prior_Upmove == True)")
    if not df_final[df_final["Prior_Upmove"]].empty:
        st.dataframe(df_final[df_final["Prior_Upmove"]][["Close", "Prior_Upmove"]].tail(5))
    else:
        st.write("Keine Prior-Upmove-Tage gefunden.")

    st.success("Analyse abgeschlossen.")
else:
    st.info("Bitte in der Seitenleiste einen Ticker eingeben und auf „Daten laden & analysieren“ klicken.")

