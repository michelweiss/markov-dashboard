#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# streamlit_market_profile.py
# -------------------------------------------------------------
# Streamlit App: Market/Volume Profile aus EOD + Intraday-Daten
# -------------------------------------------------------------

import os
import time
import asyncio
import datetime as dt
from dataclasses import dataclass
from typing import Optional, Literal, Tuple

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_datetime64tz_dtype
import httpx
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------
# ⚙️ Konfiguration
# ------------------------
DEFAULT_TOKEN_PATH = os.path.expanduser("/users/michelweiss/documents/python_for_finance/api_token.txt")
BASE_URL = "https://eodhistoricaldata.com/api"

Method = Literal["Daily Approximation", "Intraday Kerzen"]
DistMethod = Literal["uniform", "gaussian_to_typical", "close_weighted"]

# ------------------------
# 🔧 Utilities
# ------------------------

def load_api_key(path: str) -> Optional[str]:
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def daterange_default(days: int = 120) -> Tuple[dt.date, dt.date]:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    return start, end


@dataclass
class FetchConfig:
    ticker: str
    api_key: str
    date_from: dt.date
    date_to: dt.date
    interval: str = "5m"  # für Intraday


async def fetch_json(client: httpx.AsyncClient, url: str, params: dict) -> list:
    r = await client.get(url, params=params, timeout=httpx.Timeout(30.0))
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return []


async def fetch_eod(cfg: FetchConfig) -> pd.DataFrame:
    url = f"{BASE_URL}/eod/{cfg.ticker}"
    params = {
        "api_token": cfg.api_key,
        "from": cfg.date_from.isoformat(),
        "to": cfg.date_to.isoformat(),
        "period": "d",
        "fmt": "json",
        "order": "a",
    }
    async with httpx.AsyncClient() as client:
        data = await fetch_json(client, url, params)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    rename = {"date": "Date", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    df = df.rename(columns=rename)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", utc=True)
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].sort_values("Date").reset_index(drop=True)
    return df


async def fetch_intraday(cfg: FetchConfig) -> pd.DataFrame:
    # EODHD Intraday: /intraday/{ticker}?interval=1m&from=...&to=...
    url = f"{BASE_URL}/intraday/{cfg.ticker}"
    params = {
        "api_token": cfg.api_key,
        "interval": cfg.interval,
        "from": int(time.mktime(dt.datetime.combine(cfg.date_from, dt.time.min).timetuple())),
        "to": int(time.mktime(dt.datetime.combine(cfg.date_to, dt.time.max).timetuple())),
        "fmt": "json",
        "order": "a",
    }
    async with httpx.AsyncClient() as client:
        data = await fetch_json(client, url, params)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    rename = {"timestamp": "Date", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    df = df.rename(columns=rename)
    df["Date"] = pd.to_datetime(df["Date"], unit="s", errors="coerce", utc=True)
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].sort_values("Date").reset_index(drop=True)
    return df

# ------------------------
# 📈 Corporate Actions: Splits (neu)
# ------------------------

async def fetch_splits(cfg: FetchConfig) -> pd.DataFrame:
    """Holt Split-Events für den Zeitraum. EODHD liefert z. B. {'date': '2020-08-31', 'split': '4/1'}."""
    url = f"{BASE_URL}/splits/{cfg.ticker}"
    params = {
        "api_token": cfg.api_key,
        "from": cfg.date_from.isoformat(),
        "to": cfg.date_to.isoformat(),
        "fmt": "json",
    }
    try:
        async with httpx.AsyncClient() as client:
            data = await fetch_json(client, url, params)
    except Exception:
        data = []
    if not data:
        return pd.DataFrame()

    rows = []
    for it in data:
        dstr = it.get("date") or it.get("Date")
        ratio = it.get("split") or it.get("ratio") or it.get("value")
        if not dstr or ratio is None:
            continue
        rstr = str(ratio).replace(":", "/")
        try:
            if "/" in rstr:
                a, b = rstr.split("/", 1)
                num = float(a); den = float(b) if float(b) != 0 else 1.0
                f = num / den
            else:
                f = float(rstr)
        except Exception:
            continue
        try:
            d = pd.to_datetime(dstr).date()
        except Exception:
            continue
        rows.append({"Date": d, "Factor": f, "Raw": rstr})

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)


def apply_split_adjustments(df: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame:
    """
    Wendet Split-Adjustierung an: Preise / Faktor, Volumen * Faktor für alle Zeilen VOR dem Split-Datum.
    Bei mehreren Splits wird der kumulative Faktor verwendet.
    """
    if df.empty or splits is None or splits.empty:
        return df

    out = df.copy()
    dates = out["Date"].dt.date.values
    factors = np.ones(len(out), dtype=float)

    for _, r in splits.iterrows():
        sdate = r["Date"]
        f = float(r["Factor"]) if pd.notna(r["Factor"]) else 1.0
        mask = dates < sdate
        factors[mask] *= f

    # Preise anpassen (teilen), Volumen anpassen (multiplizieren)
    price_cols = [c for c in ["Open", "High", "Low", "Close"] if c in out.columns]
    if price_cols:
        out[price_cols] = out[price_cols].div(factors, axis=0)
    if "Volume" in out.columns:
        out["Volume"] = out["Volume"].mul(factors)

    return out

# ------------------------
# 📦 Volume-Profile-Bausteine
# ------------------------

def sanitize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce types, drop bad rows (NaT/NaN/inf), ensure logical ranges.
    Robust handling of timezone-aware datetime dtypes.
    """
    if df.empty:
        return df
    d = df.copy()

    # Date column → ensure pandas datetime with UTC tz
    if "Date" in d.columns:
        if not (is_datetime64_any_dtype(d["Date"]) or is_datetime64tz_dtype(d["Date"])):
            d["Date"] = pd.to_datetime(d["Date"], errors="coerce", utc=True)
        # drop NaT
        d = d[~d["Date"].isna()].copy()
        # ensure tz-aware UTC
        try:
            if getattr(d["Date"].dt, "tz", None) is None:
                d["Date"] = d["Date"].dt.tz_localize("UTC")
            else:
                d["Date"] = d["Date"].dt.tz_convert("UTC")
        except Exception:
            d["Date"] = pd.to_datetime(d["Date"], errors="coerce", utc=True)
            d = d[~d["Date"].isna()].copy()

    # Coerce numeric for OHLCV
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in d.columns:
            d[col] = pd.to_numeric(d[col], errors="coerce")

    # Remove rows with NaN/inf in OHLCV
    keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in d.columns]
    d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=keep_cols).copy()

    # Logical sanity: high>=low, volume>=0
    if {"High", "Low"}.issubset(d.columns):
        d = d[d["High"] >= d["Low"]]
    if "Volume" in d.columns:
        d = d[d["Volume"] >= 0]

    return d

def _gaussian_weights(prices: np.ndarray, center: float, scale: float) -> np.ndarray:
    w = np.exp(-0.5 * ((prices - center) / max(scale, 1e-9)) ** 2)
    s = w.sum()
    return w / s if s > 0 else np.full_like(prices, 1.0 / len(prices))


def distribute_volume_over_range(low: float, high: float, volume: float, bins: np.ndarray, method: DistMethod, close: Optional[float] = None) -> np.ndarray:
    mask = (bins >= low) & (bins <= high)
    if not mask.any() or volume <= 0:
        return np.zeros_like(bins, dtype=float)
    sel = bins[mask]

    if method == "uniform":
        w = np.full(len(sel), 1.0 / len(sel))
    elif method == "gaussian_to_typical":
        center = (high + low + (close if close is not None else (high + low) / 2)) / 3
        scale = max((high - low) / 6, 1e-6)
        w = _gaussian_weights(sel, center, scale)
    elif method == "close_weighted":
        center = close if close is not None else (high + low) / 2
        scale = max((high - low) / 6, 1e-6)
        w = _gaussian_weights(sel, center, scale)
    else:
        w = np.full(len(sel), 1.0 / len(sel))

    out = np.zeros_like(bins, dtype=float)
    out[mask] = w * volume
    return out


def build_profile_from_daily(df: pd.DataFrame, price_step: float, dist: DistMethod = "gaussian_to_typical") -> pd.Series:
    if df.empty or price_step <= 0:
        return pd.Series(dtype=float)
    df = sanitize_ohlcv(df)
    if df.empty:
        return pd.Series(dtype=float)

    pr_min = np.floor(df["Low"].min() / price_step) * price_step
    pr_max = np.ceil(df["High"].max() / price_step) * price_step
    if not np.isfinite(pr_min) or not np.isfinite(pr_max) or pr_max <= pr_min:
        return pd.Series(dtype=float)
    bins = np.asarray(np.arange(pr_min, pr_max + price_step, price_step), dtype=float)

    accum = np.zeros_like(bins, dtype=float)
    skipped = 0
    for _, r in df.iterrows():
        lo, hi, vol, clo = r.Low, r.High, r.Volume, r.Close
        if pd.isna(lo) or pd.isna(hi) or pd.isna(vol):
            skipped += 1; continue
        if not (np.isfinite(lo) and np.isfinite(hi) and np.isfinite(vol)):
            skipped += 1; continue
        if hi < lo or vol <= 0:
            skipped += 1; continue
        lo = float(lo); hi = float(hi); vol = float(vol)
        clo_f = float(clo) if pd.notna(clo) and np.isfinite(clo) else None
        accum += distribute_volume_over_range(lo, hi, vol, bins, dist, close=clo_f)

    if skipped:
        st.info(f"{skipped} Daily-Zeilen wegen invalider OHLCV übersprungen.")
    return pd.Series(accum, index=np.round(bins, 6))


def build_profile_from_intraday(df: pd.DataFrame, price_step: float, dist: DistMethod = "gaussian_to_typical") -> pd.Series:
    if df.empty or price_step <= 0:
        return pd.Series(dtype=float)
    df = sanitize_ohlcv(df)
    if df.empty:
        return pd.Series(dtype=float)

    pr_min = np.floor(df["Low"].min() / price_step) * price_step
    pr_max = np.ceil(df["High"].max() / price_step) * price_step
    if not np.isfinite(pr_min) or not np.isfinite(pr_max) or pr_max <= pr_min:
        return pd.Series(dtype=float)
    bins = np.asarray(np.arange(pr_min, pr_max + price_step, price_step), dtype=float)

    accum = np.zeros_like(bins, dtype=float)
    skipped = 0
    for _, r in df.iterrows():
        try:
            lo, hi, vol, clo = r.Low, r.High, r.Volume, r.Close
            if pd.isna(lo) or pd.isna(hi) or pd.isna(vol):
                skipped += 1; continue
            if not (np.isfinite(lo) and np.isfinite(hi) and np.isfinite(vol)):
                skipped += 1; continue
            if hi < lo or vol <= 0:
                skipped += 1; continue
            lo = float(lo); hi = float(hi); vol = float(vol)
            clo_f = float(clo) if pd.notna(clo) and np.isfinite(clo) else None
            accum += distribute_volume_over_range(lo, hi, vol, bins, dist, close=clo_f)
        except Exception:
            skipped += 1; continue

    if skipped:
        st.info(f"{skipped} Intraday-Zeilen wegen invalider OHLCV übersprungen.")
    return pd.Series(accum, index=np.round(bins, 6))


def calc_poc_and_value_area(profile: pd.Series, pct: float = 0.70) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if profile.empty:
        return None, None, None
    prof = profile.copy().sort_index()
    total = prof.sum()
    if total <= 0:
        return None, None, None

    poc_price = float(prof.idxmax())
    idx = prof.index.values
    i_poc = np.where(idx == poc_price)[0][0]
    left = i_poc; right = i_poc
    cum = prof.iloc[i_poc]

    while cum / total < pct:
        vol_left = prof.iloc[left - 1] if left - 1 >= 0 else -1
        vol_right = prof.iloc[right + 1] if right + 1 < len(prof) else -1
        if vol_left < 0 and vol_right < 0:
            break
        if vol_right > vol_left:
            right = min(right + 1, len(prof) - 1); cum += prof.iloc[right]
        else:
            left = max(left - 1, 0); cum += prof.iloc[left]
        if left == 0 and right == len(prof) - 1:
            break

    val = float(idx[left]); vah = float(idx[right])
    return poc_price, val, vah


def adjust_today_with_live(df_intraday: pd.DataFrame, live_volume_total: Optional[float]) -> pd.DataFrame:
    """Wenn live_volume_total > sum(volume of today), verteile Restvolumen auf letzte Kerze (Close-Niveau)."""
    if live_volume_total is None or df_intraday.empty:
        return df_intraday
    dti = df_intraday.copy()
    tz = "America/New_York"
    today_et = pd.Timestamp.now(tz=tz).date()
    mask_today = dti["Date"].dt.tz_convert(tz).dt.date == today_et
    if not mask_today.any():
        return dti
    vol_today = dti.loc[mask_today, "Volume"].sum()
    if live_volume_total > vol_today and mask_today.any():
        residual = live_volume_total - vol_today
        last_idx = dti.index[mask_today][-1]
        dti.loc[last_idx, "Volume"] = float(dti.loc[last_idx, "Volume"] + residual)
    return dti

# ------------------------
# 📊 Plotting
# ------------------------

def plot_price_and_profile(df_px: pd.DataFrame, profile: pd.Series, poc: Optional[float], val: Optional[float], vah: Optional[float], title: str) -> go.Figure:
    if df_px.empty or profile.empty:
        fig = go.Figure()
        fig.update_layout(height=600, title="Keine Daten")
        return fig

    prof = profile.sort_index()

    fig = make_subplots(rows=1, cols=2, column_widths=[0.25, 0.75],
                        specs=[[{"type": "xy"}, {"type": "xy"}]],
                        shared_yaxes=True, horizontal_spacing=0.02)

    # Left: Horizontal Bar (Volume Profile)
    fig.add_trace(
        go.Bar(
            x=prof.values,
            y=prof.index.astype(float),
            orientation="h",
            name="Volume",
            hovertemplate="Preis: %{y}<br>Vol: %{x}<extra></extra>",
            showlegend=False,
        ),
        row=1, col=1,
    )

    # Markiere VA und POC (als Shapes)
    shapes = []
    if val is not None and vah is not None:
        shapes.append(dict(type="rect", xref="x1", yref="y1",
                           x0=0, x1=prof.max() * 1.02, y0=val, y1=vah,
                           line=dict(width=0), fillcolor="rgba(150,150,150,0.15)"))
    if poc is not None:
        shapes.append(dict(type="line", xref="x1", yref="y1",
                           x0=0, x1=prof.max() * 1.02, y0=poc, y1=poc,
                           line=dict(color="rgba(50,50,50,0.6)", width=2, dash="dot")))

    # Right: Candles
    fig.add_trace(
        go.Candlestick(
            x=df_px["Date"],
            open=df_px["Open"], high=df_px["High"], low=df_px["Low"], close=df_px["Close"],
            name="Preis",
            showlegend=False,
        ),
        row=1, col=2,
    )

    fig.update_layout(
        title=title,
        height=750,
        bargap=0.01,
        shapes=shapes,
        xaxis1=dict(title="Volumen"),
        yaxis1=dict(title="Preis", autorange=True),
        xaxis2=dict(title="Zeit"),
    )

    return fig

# ------------------------
# 🚀 Streamlit App
# ------------------------

st.set_page_config(page_title="Market / Volume Profile (EOD + Intraday)", layout="wide")

st.sidebar.header("Parameter")
colA, colB = st.sidebar.columns(2)

def_start, def_end = daterange_default(120)

ticker = st.sidebar.text_input("Ticker", value="AAPL").strip().upper()
start_date = st.sidebar.date_input("Von", value=def_start)
end_date = st.sidebar.date_input("Bis", value=def_end)

method: Method = st.sidebar.selectbox("Profil-Methode", ["Intraday Kerzen", "Daily Approximation"], index=0)
interval = st.sidebar.selectbox("Intraday-Intervall", ["1m", "5m", "15m"], index=1, help="Nur für 'Intraday Kerzen'")

price_step = st.sidebar.number_input("Preis-Step (Bin-Größe)", min_value=0.001, value=0.50, step=0.01, format="%.3f")
dist: DistMethod = st.sidebar.selectbox("Volumenverteilung je Candle", ["gaussian_to_typical", "uniform", "close_weighted"], index=0)
va_pct = st.sidebar.slider("Value Area %", min_value=0.5, max_value=0.9, value=0.70, step=0.01)

# API-Key wird automatisch aus DEFAULT_TOKEN_PATH geladen (kein GUI-Input)
api_key = load_api_key(DEFAULT_TOKEN_PATH) or ""
live_total = st.sidebar.number_input("Heutiges Live-Gesamtvolumen (optional)", min_value=0.0, value=0.0, step=1000.0,
                                     help="Falls externe Live-Quelle > Intraday-Volumen: Rest wird der letzten Kerze zugeschlagen.")

run_btn = st.sidebar.button("📈 Profil neu berechnen")

st.title("Market / Volume Profile je Ticker")
st.caption("Quelle: EOD Historical Data. Profil = Volumen je Preisband. POC = höchstes Volumenlevel. Value Area = Preisspanne mit z.B. 70% des Gesamtvolumens.")

if run_btn:
    if not api_key:
        st.error("Kein API-Token gefunden. Bitte API-Key unter DEFAULT_TOKEN_PATH hinterlegen.")
        st.stop()

    cfg = FetchConfig(ticker=ticker, api_key=api_key, date_from=start_date, date_to=end_date, interval=interval)

    with st.status("Daten laden …", expanded=False) as status:
        splits_df = pd.DataFrame()

        if method == "Intraday Kerzen":
            df_px = asyncio.run(fetch_intraday(cfg))
            # Splits anwenden (Preise÷, Volumen×) für alle älteren Kerzen
            try:
                splits_df = asyncio.run(fetch_splits(cfg))
                if not splits_df.empty:
                    df_px = apply_split_adjustments(df_px, splits_df)
                    status.update(label=f"Splits angewandt: {len(splits_df)} Event(s)")
            except Exception:
                pass

            if live_total and live_total > 0:
                df_px = adjust_today_with_live(df_px, live_total)

            status.update(label="Baue Intraday-Volume-Profile …")
            profile = build_profile_from_intraday(df_px, price_step=price_step, dist=dist)

        else:
            df_px = asyncio.run(fetch_eod(cfg))
            # Splits anwenden
            try:
                splits_df = asyncio.run(fetch_splits(cfg))
                if not splits_df.empty:
                    df_px = apply_split_adjustments(df_px, splits_df)
                    status.update(label=f"Splits angewandt: {len(splits_df)} Event(s)")
            except Exception:
                pass

            status.update(label="Baue Daily-Approximation …")
            profile = build_profile_from_daily(df_px, price_step=price_step, dist=dist)

        poc, val, vah = calc_poc_and_value_area(profile, pct=va_pct)
        status.update(label="Plotte", state="complete")

    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric("POC", f"{poc:.4f}" if poc is not None else "-")
        st.metric("VAL", f"{val:.4f}" if val is not None else "-")
        st.metric("VAH", f"{vah:.4f}" if vah is not None else "-")
        st.metric("Gesamtvolumen", f"{profile.sum():,.0f}")

    fig = plot_price_and_profile(df_px, profile, poc, val, vah, title=f"{ticker} · {method}")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Debug / Datenvorschau"):
        st.write("Preis-Daten:")
        st.dataframe(df_px.tail(200))
        st.write("Volume Profile (Top 100 by Vol):")
        st.dataframe(profile.sort_values(ascending=False).head(100))
        if not splits_df.empty:
            st.write("Splits im Zeitraum:")
            st.dataframe(splits_df)

else:
    st.info("Parameter setzen und 'Profil neu berechnen' klicken.")

# ------------------------
# 📌 Hinweise
# - Daily Approximation ist grob und eignet sich vor allem für längere Historie/Levels.
# - Intraday (1m/5m/15m) liefert ein deutlich realistischeres Profil.
# - Split-Adjustierung: historische OHLC werden durch den kumulativen Split-Faktor geteilt, Volumen damit multipliziert.
# ------------------------

