#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
#  Regime Loader – universumsbasiertes Laden des Market Bias
#  • Primär: trader/day_trading/market_bias_<universe>.json
#  • Legacy-Fallback: Markov/market_bias_<universe>.json
#  • Notfall-Fallback: aus fusion_bias_nasdaq100_{weekly,monthly}.json ableiten
# ------------------------------------------------------------------

import os
import json
from datetime import datetime

BASE = os.path.expanduser("~/Documents/Python_for_Finance/Markov")
DAY_DIR = os.path.join(BASE, "trader", "day_trading")

DEFAULTS = {
    "bias": "NEUTRAL",
    "granularity": "weekly",
    "bias_date": datetime.now().strftime("%Y-%m-%d"),
    "persist_days": 0,
    "triple_long": 0,
    "triple_short": 0,
}

def _load_json(path: str) -> dict | None:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️  Fehler beim Laden von {path}: {e}")
    return None

def _apply_defaults(d: dict) -> dict:
    out = dict(DEFAULTS)
    out.update({k: v for k, v in (d or {}).items() if v is not None})
    # Sanitizing
    out["bias"] = (out.get("bias") or "NEUTRAL").upper()
    if out["bias"] not in ("BULL", "BEAR", "NEUTRAL", "MILD_BULL", "MILD_BEAR"):
        out["bias"] = "NEUTRAL"
    out["granularity"] = (out.get("granularity") or "weekly").lower()
    return out

def _from_fusion_bias() -> dict | None:
    """Leitet einen Bias aus den fusion_bias-NASDAQ100-Files ab (neu in day_trading)."""
    paths = []
    for freq in ("weekly", "monthly"):
        paths.append((freq, os.path.join(DAY_DIR, f"fusion_bias_nasdaq100_{freq}.json")))
        # Legacy-Fallback (falls noch nicht umgestellt)
        paths.append((freq, os.path.join(BASE, "trader", f"fusion_bias_nasdaq100_{freq}.json")))

    candidates = []
    for freq, p in paths:
        js = _load_json(p)
        if js:
            # 'updated' bevorzugen, sonst 'bias_date'
            ts = js.get("updated") or js.get("bias_date") or ""
            try:
                when = datetime.fromisoformat(ts.replace("Z", ""))
            except Exception:
                when = datetime.min
            candidates.append((when, freq, js, p))

    if not candidates:
        return None

    # Jüngste Datei gewinnt
    candidates.sort(key=lambda t: t[0], reverse=True)
    _, freq, js, p = candidates[0]

    # sentiment → bias Mappings
    sentiment = (js.get("sentiment") or "").upper()
    bias = "NEUTRAL"
    if sentiment in ("BULL", "MILD_BULL"):
        bias = sentiment
    elif sentiment in ("BEAR", "MILD_BEAR"):
        bias = sentiment

    out = {
        "bias": bias,
        "granularity": (js.get("freq") or freq or "weekly"),
        "bias_date": js.get("bias_date") or datetime.now().strftime("%Y-%m-%d"),
        "persist_days": 0,
        "triple_long": 0,
        "triple_short": 0,
        # optional nützlich:
        # "ratio": js.get("ratio"),
        # "count_long": js.get("count_long"),
        # "count_short": js.get("count_short"),
        # "source_path": p,
    }
    print(f"ℹ️  Bias aus Fusion-Datei abgeleitet: {os.path.basename(p)} → {out['bias']} ({out['granularity']})")
    return _apply_defaults(out)

def load_market_bias(universe: str = "NASDAQ100") -> dict:
    """Lädt den letzten Market Bias (neu: aus day_trading)."""
    # 1) Neuer Zielpfad
    new_path = os.path.join(DAY_DIR, f"market_bias_{universe.lower()}.json")
    js = _load_json(new_path)
    if js:
        return _apply_defaults(js)

    # 2) Legacy-Pfad (Root)
    old_path = os.path.join(BASE, f"market_bias_{universe.lower()}.json")
    js = _load_json(old_path)
    if js:
        print("ℹ️  Legacy-Market-Bias verwendet (bitte migrieren → day_trading).")
        return _apply_defaults(js)

    # 3) Notfall: aus fusion_bias ableiten (weekly/monthly – jüngster gewinnt)
    derived = _from_fusion_bias()
    if derived:
        return derived

    print(f"⚠️  Market Bias JSON fehlt (neu & legacy). Fallback=NEUTRAL.")
    return dict(DEFAULTS)

