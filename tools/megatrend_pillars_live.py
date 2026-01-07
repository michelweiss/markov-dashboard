#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import pandas as pd
from tools.megatrend_adapter import get_prices, get_fundamentals

def fx_to_usd(value, currency):
    if value is None:
        return None
    
    try:
        value = float(value)
    except:
        return None

    if currency == "USD" or currency is None:
        return value

    # FIXER EUR→USD Proxy (konservativ, kein Live-FX nötig)
    if currency == "EUR":
        return value * 1.08
    if currency == "CHF":
        return value * 1.12
    if currency == "GBP":
        return value * 1.27

    return value


def _calc_ret(px: pd.DataFrame, days: int) -> float:
    """Sichere Return-Berechnung mit Längen-Check."""
    if px is None or px.empty:
        return np.nan
    if len(px) <= days:
        return np.nan
    try:
        return px["close"].iloc[-1] / px["close"].iloc[-days] - 1
    except Exception:
        return np.nan


# -----------------------------
# MOMENTUM (M)
# -----------------------------
def momentum_score(tickers):
    rets = []

    for t in tickers:
        px = get_prices(t, years=2)
        r3  = _calc_ret(px, 63)   # ~3M
        r6  = _calc_ret(px, 126)  # ~6M
        r12 = _calc_ret(px, 252)  # ~12M
        if not np.isnan(np.nanmean([r3, r6, r12])):
            rets.append(np.nanmean([r3, r6, r12]))

    if not rets:
        return 0.5  # neutral

    m = float(np.nanmean(rets))
    # Grobe Skalierung auf 0..1 (Tuning möglich)
    return float(np.clip((m + 0.20) / 0.60, 0.0, 1.0))


# -----------------------------
# EVIDENCE (E)
# -----------------------------
def evidence_score(tickers):
    """
    Evidence = harte ökonomische Bestätigung
    - Aktien (US/EU/Asia): Revenue-Growth (YoY oder Halbjahr)
    - ETFs: AUM-Growth (YoY) oder Preis-Fallback
    Skala 0..1
    """
    vals = []

    for t in tickers:
        f = get_fundamentals(t)
        gen = f.get("General", {})
        is_etf = gen.get("Type", "").lower() == "etf"

        # -----------------------------
        # ETF: AUM-Growth oder Preis-Fallback
        # -----------------------------
        if is_etf:
            aum_now = gen.get("AssetsUnderManagement")
            aum_prev = gen.get("AssetsUnderManagementPreviousYear")

            try:
                if aum_now and aum_prev and float(aum_prev) > 0:
                    g = float(aum_now) / float(aum_prev) - 1.0
                    vals.append(g)
                    continue
            except Exception:
                pass

            # Preis-Fallback (6M)
            px = get_prices(t, years=1)
            if not px.empty and len(px) > 126:
                try:
                    r6 = px["close"].iloc[-1] / px["close"].iloc[-126] - 1
                    vals.append(r6)
                except Exception:
                    pass

            continue  # nächster Ticker

        # -----------------------------
        # AKTIE: Quarterly → Halbjahr → Yearly
        # -----------------------------
        stmts_q = (
            f.get("Financials", {})
             .get("Income_Statement", {})
             .get("quarterly", {})
        )
        stmts_y = (
            f.get("Financials", {})
             .get("Income_Statement", {})
             .get("yearly", {})
        )

        growth = None

        try:
            q_vals = list(stmts_q.values()) if isinstance(stmts_q, dict) else []
            y_vals = list(stmts_y.values()) if isinstance(stmts_y, dict) else []

            # 1️⃣ Quarterly YoY (4 Quartale Rückblick)
            if len(q_vals) >= 5:
                last = q_vals[0].get("totalRevenue")
                prev = q_vals[4].get("totalRevenue")
                if last and prev and float(prev) > 0:
                    growth = float(last) / float(prev) - 1.0

            # 2️⃣ Halbjahr (EU/Asia Fallback)
            elif len(q_vals) >= 3:
                last = q_vals[0].get("totalRevenue")
                prev = q_vals[2].get("totalRevenue")
                if last and prev and float(prev) > 0:
                    growth = float(last) / float(prev) - 1.0

            # 3️⃣ Yearly Fallback
            elif len(y_vals) >= 2:
                last = y_vals[0].get("totalRevenue")
                prev = y_vals[1].get("totalRevenue")
                if last and prev and float(prev) > 0:
                    growth = float(last) / float(prev) - 1.0

        except Exception:
            growth = None

        if growth is not None:
            vals.append(growth)

    if not vals:
        return 0.5  # neutral

    g = float(np.nanmean(vals))

    # Normierung: -10% → 0.3 | 0% → 0.5 | +30% → 0.9
    score = (g + 0.10) / 0.40
    return float(np.clip(score, 0.0, 1.0))


# -----------------------------
# INVESTIERBARKEIT (I)
# -----------------------------
def extract_usd_size(fundamental, highlights, general, is_etf=False):
    cur = general.get("CurrencyCode")

    if is_etf:
        aum = general.get("AssetsUnderManagement")
        if aum:
            return fx_to_usd(aum, cur)
    
    mc = highlights.get("MarketCapitalizationMln")
    if mc:
        return fx_to_usd(mc * 1_000_000, cur)

    mc_raw = general.get("MarketCapitalization")
    if mc_raw:
        return fx_to_usd(mc_raw, cur)

    return None


def investability_score(tickers):

    sizes = []
    
    for ticker in tickers:
        try:
            general = eod_client.get_fundamental_equity(ticker, filter_="General")
            highlights = eod_client.get_fundamental_equity(ticker, filter_="Highlights")

            is_etf = general.get("Type") == "ETF"
            size_usd = extract_usd_size(highlights, highlights, general, is_etf)

            if size_usd and size_usd > 0:
                sizes.append(size_usd)

        except:
            continue

    if not sizes:
        return 0.3   # Small / illiquid default

    avg_size = np.mean(sizes)

    # Logarithmische Skalierung
    if avg_size > 500e9:
        return 1.0
    elif avg_size > 100e9:
        return 0.85
    elif avg_size > 20e9:
        return 0.70
    elif avg_size > 5e9:
        return 0.55
    elif avg_size > 1e9:
        return 0.45
    else:
        return 0.30



# -----------------------------
# RISK (R)
# -----------------------------
def risk_score(tickers):
    vols = []

    for t in tickers:
        px = get_prices(t, years=1)
        if px is None or px.empty:
            continue
        try:
            ret = px["close"].pct_change()
            v = ret.std()
            if not np.isnan(v):
                vols.append(v)
        except Exception:
            continue

    if not vols:
        return 0.5

    v = float(np.nanmean(vols))
    # invertiert → hohe Vol = niedriger Score
    return float(np.clip(1.0 - v * 6.0, 0.0, 1.0))

