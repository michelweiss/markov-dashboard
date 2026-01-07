#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ======================================================================
# 🧭 update_market_bias.py
# Kombiniert Weekly + Monthly Bias in market_bias.json
#  - Läuft nach Screener-Fusion (weekly + monthly)
#  - Schreibt in trader/intraday_trader/
#  - Wählt automatisch Quelle je nach Datum
#  - Enthält "gültig bis" Felder pro Frequenz
# ======================================================================

import os, json, calendar
from datetime import datetime
import pandas as pd  # für Week/MonthEnd-Offsets

# ─────────────────────────────────────────────────────────────
# 📁 Pfade (vereinheitlicht)
# ─────────────────────────────────────────────────────────────
BASE_MARKOV = "/Users/michelweiss/Documents/Python_for_Finance/Markov"
TRADER_DIR  = os.path.join(BASE_MARKOV, "trader")
INTRA_DIR   = os.path.join(TRADER_DIR, "intraday_trader")
LEGACY_DIR  = os.path.join(TRADER_DIR, "day_trading")
os.makedirs(INTRA_DIR, exist_ok=True)

def first_existing(*paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]

OUT_DIR = first_existing(INTRA_DIR, LEGACY_DIR)

# Primäre Dateien (neu in intraday_trader/)
WEEKLY_FILE  = os.path.join(OUT_DIR, "fusion_bias_nasdaq100_weekly.json")
MONTHLY_FILE = os.path.join(OUT_DIR, "fusion_bias_nasdaq100_monthly.json")
OUT_FILE     = os.path.join(OUT_DIR, "market_bias.json")

# Legacy-Fallbacks (werden nur verwendet, falls obige fehlen)
WEEKLY_OLD  = os.path.join(TRADER_DIR, "fusion_bias_nasdaq100_weekly.json")
MONTHLY_OLD = os.path.join(TRADER_DIR, "fusion_bias_nasdaq100_monthly.json")

# ─────────────────────────────────────────────────────────────
# ⚙️ Helper
# ─────────────────────────────────────────────────────────────
def load_json(path: str):
    """Lädt JSON sicher oder gibt None zurück."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def is_month_end() -> bool:
    """True, wenn heute letzter Kalendertag des Monats."""
    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day == last_day

def compute_valid_until(as_of: str, freq: str) -> str:
    """Berechnet Gültigkeitsende (Sonntag / Monatsultimo)."""
    try:
        d = pd.to_datetime(as_of)
    except Exception:
        d = pd.Timestamp.today()
    if freq == "weekly":
        return (d + pd.offsets.Week(weekday=6)).strftime("%Y-%m-%d")  # bis Sonntag
    elif freq == "monthly":
        return (d + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
    return d.strftime("%Y-%m-%d")

# ─────────────────────────────────────────────────────────────
# 🚀 Main
# ─────────────────────────────────────────────────────────────
def main():
    print("🧭 Starte Market Bias Update …")

    # Primär aus intraday_trader, sonst Fallback aus trader/
    weekly  = load_json(WEEKLY_FILE)  or load_json(WEEKLY_OLD)
    monthly = load_json(MONTHLY_FILE) or load_json(MONTHLY_OLD)

    if not weekly and not monthly:
        raise SystemExit("❌ Keine Bias-Dateien gefunden (weder weekly noch monthly).")

    # Quelle bestimmen
    active_source = "monthly" if (is_month_end() and monthly) else "weekly"
    active = monthly if active_source == "monthly" else weekly

    # Safety Fallback
    if not active:
        active_source = "weekly" if weekly else "monthly"
        active = weekly or monthly

    # As-of extrahieren
    as_of_weekly  = weekly.get("as_of")  if weekly  else None
    as_of_monthly = monthly.get("as_of") if monthly else None

    # Gültigkeitsenden berechnen
    valid_until_weekly  = compute_valid_until(as_of_weekly, "weekly")   if as_of_weekly  else None
    valid_until_monthly = compute_valid_until(as_of_monthly, "monthly") if as_of_monthly else None

    # 📊 Zusammenfassung erzeugen
    bias_out = {
        "bias_date": datetime.now().strftime("%Y-%m-%d"),
        "active_source": active_source,
        "final_bias": active.get("sentiment", "NEUTRAL"),
        "weekly_ratio":  weekly.get("ratio")  if weekly  else None,
        "monthly_ratio": monthly.get("ratio") if monthly else None,
        "weekly_sentiment":  weekly.get("sentiment")  if weekly  else None,
        "monthly_sentiment": monthly.get("sentiment") if monthly else None,
        "as_of_weekly":  as_of_weekly,
        "as_of_monthly": as_of_monthly,
        "valid_until_weekly":  valid_until_weekly,
        "valid_until_monthly": valid_until_monthly,
        "double_longs":  active.get("double_longs", []),
        "double_shorts": active.get("double_shorts", []),
        "leverage_long":  active.get("leverage_long", 1.0),
        "leverage_short": active.get("leverage_short", 1.0),
        "updated": datetime.now().isoformat(timespec="seconds"),
        "source_files": {
            "weekly":  WEEKLY_FILE,
            "monthly": MONTHLY_FILE
        }
    }

    # 📦 Speichern
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(bias_out, f, indent=2, ensure_ascii=False)

    # 🧾 Ausgabe
    print("✅ market_bias.json aktualisiert")
    print(f"   🔹 Quelle: {active_source}")
    print(f"   ⚖️ Sentiment: {bias_out['final_bias']}  ·  Lev L/S={bias_out['leverage_long']}/{bias_out['leverage_short']}")
    print(f"   📆 Weekly gültig bis:  {valid_until_weekly}")
    print(f"   📆 Monthly gültig bis: {valid_until_monthly}")
    print(f"   💾 Datei: {OUT_FILE}")

# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()

