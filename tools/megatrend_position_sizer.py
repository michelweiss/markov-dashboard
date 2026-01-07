#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Megatrend → Positions-Sizing
----------------------------
Finales Gewicht pro Einzeltitel basierend auf:

1) Megatrend-Weight (aus current_allocation.json)
2) Trend-Delta-Faktor (aus trend_delta_overlay.json)
3) Markov-Qualitätsfaktor p_up (aus Screener-JSON)
"""

import json
from pathlib import Path
import datetime as dt


# -------------------------------------------------
# Pfade
# -------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent      # → .../Markov

P_UP_FILE   = ROOT / "trader" / "data" / "p_up_by_ticker_daily.json"
MEGATREND_DIR = ROOT / "trader" / "megatrend"

ALLOC_FILE  = MEGATREND_DIR / "data" / "current_allocation.json"
DELTA_FILE  = MEGATREND_DIR / "data" / "trend_delta_overlay.json"
OUT_FILE    = MEGATREND_DIR / "data" / "positions_megatrend.json"


# -------------------------------------------------
# Parameter
# -------------------------------------------------
ACCEL_BASE = 1.0        # Platzhalter für spätere Trend-Acceleration
P_UP_BASE  = 1.0
P_UP_MULT  = 0.5


# -------------------------------------------------
# p_up aus Screener laden
# -------------------------------------------------
def load_p_up_by_ticker():
    if not P_UP_FILE.exists():
        print("⚠️ p_up File nicht gefunden:", P_UP_FILE)
        return {}

    try:
        with open(P_UP_FILE, "r", encoding="utf-8") as f:
            js = json.load(f)
        return js.get("values", {})
    except Exception as e:
        print("⚠️ Fehler beim Laden von p_up:", e)
        return {}


# -------------------------------------------------
# Trend-Delta-Faktoren laden
# -------------------------------------------------
def load_trend_delta():
    if not DELTA_FILE.exists():
        print("⚠️ Trend-Delta-Overlay nicht gefunden → neutral verwendet")
        return {}

    try:
        with open(DELTA_FILE, "r", encoding="utf-8") as f:
            js = json.load(f)

        # ✅ KORREKT: overlay → overlay_factor extrahieren
        overlay = js.get("overlay", {})

        delta_map = {}
        for trend, data in overlay.items():
            if "overlay_factor" in data:
                delta_map[trend.strip()] = float(data["overlay_factor"])

        if not delta_map:
            print("⚠️ Trend-Delta geladen, aber keine overlay_factors gefunden")

        return delta_map

    except Exception as e:
        print("⚠️ Fehler beim Laden von Trend-Delta:", e)
        return {}


# -------------------------------------------------
# Markov-Faktor aus p_up
# -------------------------------------------------
def markov_factor_from_pup(p: float) -> float:
    if p < 0.45:
        return 0.85
    elif p < 0.55:
        return 1.00
    elif p < 0.65:
        return 1.10
    elif p < 0.75:
        return 1.20
    else:
        return 1.30


# -------------------------------------------------
# Position Sizing Kernfunktion
# -------------------------------------------------
def compute_positions():

    if not ALLOC_FILE.exists():
        raise FileNotFoundError("❌ current_allocation.json nicht gefunden")

    with open(ALLOC_FILE, "r", encoding="utf-8") as f:
        alloc = json.load(f)

    p_up_map   = load_p_up_by_ticker()
    delta_map  = load_trend_delta()

    positions_raw = {}
    debug = {}

    for trend, data in alloc["trends"].items():

        w_trend = float(data["weight"])
        tickers = data.get("tickers", [])

        if not tickers:
            continue

        # ✅ Trend-Delta-Faktor (Fallback = 1.0)
        trend_delta_factor = float(delta_map.get(trend, 1.0))

        # ✅ Basisgewicht je Titel (vor Delta & Markov)
        w_each = (w_trend * trend_delta_factor) / len(tickers)

        for t in tickers:

            p_up = float(p_up_map.get(t, 0.5))

            accel_factor  = ACCEL_BASE
            markov_factor = markov_factor_from_pup(p_up)

            final_w = w_each * accel_factor * markov_factor

            positions_raw[t] = positions_raw.get(t, 0) + final_w

            debug[t] = {
                "trend": trend,
                "trend_weight": round(w_trend, 4),
                "trend_delta_factor": round(trend_delta_factor, 4),
                "base_weight": round(w_each, 6),
                "p_up": round(p_up, 3),
                "accel_factor": round(accel_factor, 3),
                "markov_factor": round(markov_factor, 3),
                "raw_weight": round(final_w, 6),
            }

    # -------------------------------------------------
    # Normalisieren auf 100 %
    # -------------------------------------------------
    total = sum(positions_raw.values())

    if total <= 0:
        print("⚠️ Keine gültigen Gewichte berechnet – Positionsliste leer")
        positions = {}
    else:
        positions = {k: round(v / total, 6) for k, v in positions_raw.items()}

    out = {
        "as_of": alloc.get("as_of", dt.date.today().isoformat()),
        "model": "Megatrend × Delta × Markov",
        "positions": positions,
        "debug": debug,
        "trend_delta_used": delta_map,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    return out


# -------------------------------------------------
# CLI Testlauf
# -------------------------------------------------
if __name__ == "__main__":

    res = compute_positions()

    print("\n✅ Positions-Sizing mit Trend-Delta erstellt:\n")
    for k, v in res["positions"].items():
        print(f"{k:6s} → {v:.3%}")

    print("\n📁 Output:", OUT_FILE)

    # 100%-Kontrolle
    s = sum(res["positions"].values())
    assert 0.999 <= s <= 1.001, f"❌ Gewichte nicht normiert: {s}"

