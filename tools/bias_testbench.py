#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json
import pandas as pd
import numpy as np
from datetime import datetime

BASE = os.path.expanduser("~/Documents/Python_for_Finance/Markov")
PATH_HIST = os.path.join(BASE, "bias_history.json")   # enthält weekly/monthly Bias
# Optional: Benchmark-Preise laden (CSV o. ä.) und in returns umwandeln
# Für die Demo nehmen wir eine Dummy-Renditeserie (0.05%/Tag):
def load_returns():
    idx = pd.date_range("2022-01-01", datetime.today(), freq="B")
    return pd.Series(0.0005, index=idx, name="ret")   # ersetze durch echte Serie

def _load_hist():
    with open(PATH_HIST, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Erwartet Liste von Einträgen mit Keys: date, weekly_bias, monthly_bias, bias (optional)
    df = pd.DataFrame(raw)
    # Robustheit
    for k in ["date","weekly_bias","monthly_bias","bias"]:
        if k not in df.columns: df[k] = None
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").drop_duplicates("date")
    # Für die Persistenz nur wöchentliches Raster verwenden
    df["weekly_bias"]  = df["weekly_bias"].fillna("NEUTRAL").str.upper()
    df["monthly_bias"] = df["monthly_bias"].fillna("NEUTRAL").str.upper()
    return df.set_index("date")

def simulate_modes(
    hist_df: pd.DataFrame,
    thresh_long_to_short: int = 5,
    thresh_short_to_long: int = 3,
    fast_exit: bool = True,
    neutral_policy: str = "LONG",   # "LONG" oder "FLAT"
) -> pd.Series:
    """
    Gibt eine tägliche Serie zurück mit Werten in {"LONG","SHORT","NEUTRAL"}.
    Persistenz basiert auf Wochenpunkten (Index von hist_df).
    """
    # Wochenpunkte → tägliche Timeline
    start = hist_df.index.min()
    end   = hist_df.index.max()
    days  = pd.date_range(start, end, freq="B")

    last_bias = "LONG"   # Startannahme
    persist_cnt = 0
    target_bias = last_bias

    # Wir iterieren über Wochenpunkte und erzeugen dort ggf. Umschaltlogik
    records = []
    for t, row in hist_df.iterrows():
        wb = (row.get("weekly_bias")  or "NEUTRAL").upper()
        mb = (row.get("monthly_bias") or "NEUTRAL").upper()

        # Kandidat: konsolidierte Richtung anhand der Gegenseite zu last_bias
        # Wenn weekly==monthly und != last_bias → Persistenz aufbauen
        # Sonst persist_cnt resetten
        if wb == mb and wb in ("LONG","SHORT"):
            candidate = wb
            same_as_last = (candidate == last_bias)

            # Fast-Exit: wenn beide Skalen auf *Gegenseite* drehen, sofort umschalten
            if fast_exit and not same_as_last:
                last_bias = candidate
                persist_cnt = 0
            else:
                if same_as_last:
                    persist_cnt = 0  # nichts zu tun
                else:
                    persist_cnt += 1
                    # Schwelle abhängig von Richtung
                    thr = (thresh_long_to_short if candidate == "SHORT" else thresh_short_to_long)
                    if persist_cnt >= thr:
                        last_bias = candidate
                        persist_cnt = 0
        else:
            # Keine klare Bestätigung / NEUTRAL → Persistenz auf 0
            persist_cnt = 0
            # last_bias bleibt

        records.append((t, last_bias))

    wk_modes = pd.Series({t: b for t, b in records}).sort_index()
    # Auf tägliche Tage vorwärts füllen
    daily_modes = wk_modes.reindex(days, method="ffill")
    # NEUTRAL-Politik: falls neutral_policy="LONG", dann NEUTRAL → LONG (hier haben wir bereits last_bias ohne neutral)
    # Falls explizit echte "NEUTRAL" gewünscht (flat), überschreibbar:
    if neutral_policy == "FLAT":
        # Option: wenn weekly!=monthly → NEUTRAL statt last_bias
        # Erzeuge an Wochenpunkten Neutralflags:
        neutral_flags = []
        for t, row in hist_df.iterrows():
            wb = (row.get("weekly_bias")  or "NEUTRAL").upper()
            mb = (row.get("monthly_bias") or "NEUTRAL").upper()
            neutral_flags.append((t, not (wb == mb and wb in ("LONG","SHORT"))))
        nf = pd.Series({t:f for t,f in neutral_flags}).reindex(days, method="ffill").fillna(True)
        daily_modes = np.where(nf, "NEUTRAL", daily_modes)
        daily_modes = pd.Series(daily_modes, index=days)
    return daily_modes.rename("mode")

def evaluate(returns: pd.Series, modes: pd.Series, whipsaw_window_weeks: int = 4, rf_annual: float = 0.0):
    # Align
    ret = returns.reindex(modes.index).fillna(0.0)
    side = modes.map({"LONG":1.0, "SHORT":-1.0, "NEUTRAL":0.0}).astype(float)
    strat = (ret * side).rename("strat_ret")

    # Metriken
    def cagr(rs):
        if rs.empty: return np.nan
        tot = (1 + rs).prod()
        yrs = (rs.index[-1] - rs.index[0]).days / 365.25
        return tot**(1/yrs) - 1 if yrs > 0 else np.nan

    def maxdd(rs):
        eq = (1 + rs).cumprod()
        roll_max = eq.cummax()
        dd = eq/roll_max - 1
        return dd.min()

    def sharpe(rs, rf=0.0):
        # rf annual → daily approx.
        rf_daily = (1+rf)**(1/252)-1
        excess = rs - rf_daily
        mu = excess.mean()*252
        sd = excess.std(ddof=0)*np.sqrt(252)
        return mu/sd if sd>0 else np.nan

    # Regime-Stats
    switches = (modes != modes.shift(1)).sum()
    # Whipsaw: Wechsel hin und zurück innerhalb von N Wochen
    regime_starts = modes[modes != modes.shift(1)]
    whipsaws = 0
    for i in range(1, len(regime_starts)):
        dur_days = (regime_starts.index[i] - regime_starts.index[i-1]).days
        if dur_days <= 7*whipsaw_window_weeks:
            whipsaws += 1

    # Ø-Regime-Dauer
    if not regime_starts.empty:
        durs = regime_starts.index.to_series().diff().dropna().dt.days
        avg_regime_days = durs.mean()
    else:
        avg_regime_days = np.nan

    out = {
        "CAGR": cagr(strat),
        "Sharpe": sharpe(strat, rf_annual),
        "MaxDD": maxdd(strat),
        "HitRate": (strat > 0).mean(),
        "Trades": (side != side.shift(1)).sum(),  # grob
        "Switches": int(switches),
        "Whipsaws(≤4W)": int(whipsaws),
        "%LongDays": (modes == "LONG").mean(),
        "%ShortDays": (modes == "SHORT").mean(),
        "AvgRegimeDays": avg_regime_days,
    }
    return pd.Series(out)

def grid_search(hist_df, returns,
                l2s_range=range(3,9), s2l_range=range(2,7), fast_exit_opts=(True, False),
                neutral_policy="LONG", rf_annual=0.0):
    rows = []
    for L2S in l2s_range:
        for S2L in s2l_range:
            for fx in fast_exit_opts:
                modes = simulate_modes(hist_df, L2S, S2L, fast_exit=fx, neutral_policy=neutral_policy)
                met = evaluate(returns, modes, rf_annual=rf_annual).to_dict()
                met.update({"L2S":L2S, "S2L":S2L, "FastExit":fx})
                rows.append(met)
    df = pd.DataFrame(rows).sort_values(["Sharpe","CAGR"], ascending=False)
    return df

if __name__ == "__main__":
    hist = _load_hist()
    rets = load_returns()  # <-- hier deine echte Serie einspeisen
    # Beispiel: Asymmetrisch 5/3 + Fast-Exit
    modes_53 = simulate_modes(hist, 5, 3, fast_exit=True, neutral_policy="LONG")
    print(evaluate(rets, modes_53, rf_annual=0.02).round(4).to_dict())

    # Grid-Search
    gs = grid_search(hist, rets, rf_annual=0.02)
    print(gs.head(10).round(4))

