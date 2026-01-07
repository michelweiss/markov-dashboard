#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
#  Daily Trader Runner – Weekly-Anker-sicher + Overall-Regime-Integration
#  • berücksichtigt granularity="weekly" & anchor_friday (W-FRI)
#  • asymmetrische Persistenz (5/3)
#  • Konsenssteuerung über overall_regime.json (Meta-Markov + High/Low)
#  • Auto-Launch des passenden Traders (LONG/SHORT)
# ------------------------------------------------------------------

import os
import sys
import json
import logging
import subprocess
from datetime import datetime, timedelta
import pandas_market_calendars as mcal
import pandas as pd
import pytz

# ------------------------------------------------------------------
# 🧩 PATH BOOTSTRAP – muss vor allen tools-Imports stehen
# ------------------------------------------------------------------
MARKOV_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR   = os.path.join(MARKOV_ROOT, "tools")

for p in (MARKOV_ROOT, TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

# ------------------------------------------------------------------
# 🧩 Safe Import regime_loader + Fallback
# ------------------------------------------------------------------
try:
    from tools.regime_loader import load_market_bias
except Exception:
    import json
    def load_market_bias(universe: str):
        """Fallback: liest universumsspezifische Bias-Datei direkt."""
        path = os.path.expanduser(
            f"~/Documents/Python_for_Finance/Markov/market_bias_{universe.lower()}.json"
        )
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"bias": "NEUTRAL", "triple_long": 0, "triple_short": 0}

# ------------------------------------------------------------------
# 🧠 BASIS-PFADE
# ------------------------------------------------------------------
BASE = os.path.expanduser("~/Documents/Python_for_Finance/Markov")
LOG_DIR = os.path.join(BASE, "Log_Files")

PATH_BIAS    = os.path.join(BASE, "market_bias.json")
PATH_STATE   = os.path.join(BASE, "trader_state.json")
PATH_OVERALL = os.path.join(BASE, "overall_regime.json")
PATH_LOGRUN  = os.path.join(BASE, "trader_cron.log")

# ---------------------- Settings ----------------------
THRESH_LONG_TO_SHORT = 5   # LONG→SHORT
THRESH_SHORT_TO_LONG = 3   # SHORT→LONG
NEUTRAL_DEFAULT_MODE = "LONG"
# -------------------------------------------------------

# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────
def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"⚠️  Konnte {os.path.basename(path)} nicht laden: {e}")
    return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"❌  Fehler beim Speichern {os.path.basename(path)}: {e}")


def latest_bias_log():
    try:
        files = [f for f in os.listdir(LOG_DIR)
                 if f.startswith("market_bias_") and f.endswith(".json")]
        if not files:
            return None
        files.sort(reverse=True)
        return os.path.join(LOG_DIR, files[0])
    except Exception:
        return None


def get_weekly_anchor():
    """Bestimmt letzten NYSE-Handelstag der aktuellen W-FRI-Woche."""
    tz = pytz.timezone("America/New_York")
    today = datetime.now(tz).date()
    cal = mcal.get_calendar("XNYS")
    sched = cal.schedule(start_date=today - timedelta(days=14),
                         end_date=today + timedelta(days=1))
    sessions = pd.DatetimeIndex(sched.index).tz_localize("UTC").tz_convert(tz).normalize()
    sessions = sessions.tz_localize(None)  # Period drop tz warning vermeiden
    current_wfri = pd.Timestamp(today).to_period("W-FRI")
    mask = sessions.to_period("W-FRI") == current_wfri
    week_sessions = sessions[mask]
    if len(week_sessions) == 0:
        return sessions.max().date()
    return week_sessions.max().date()


def load_overall_regime():
    """Liest overall_regime.json (Meta-Konsens mit Long-Default)."""
    try:
        if os.path.exists(PATH_OVERALL):
            with open(PATH_OVERALL, "r", encoding="utf-8") as f:
                js = json.load(f)
                regime = js.get("overall_regime", "BULL").upper()
                if regime not in ("BULL", "BEAR", "NEUTRAL"):
                    regime = "BULL"
                return regime
    except Exception as e:
        logging.warning(f"⚠️  Konnte overall_regime.json nicht laden: {e}")
    return "BULL"  # Fallback: Long-Default

# ──────────────────────────────────────────────
# Bias-Entscheidung (mit Weekly-Schutz)
# ──────────────────────────────────────────────
def decide_next_mode(bias: dict, state: dict):
    """Entscheidet anhand asymmetrischer Persistenz über den nächsten Trader-Modus."""
    bias_mode = (bias.get("bias") or bias.get("bias_mode") or "NEUTRAL").upper()

    # 🧩 Mapping "BULL"/"BEAR"
    if bias_mode == "BULL":
        logging.info("🔁 Mapping Bias: BULL → LONG")
        bias_mode = "LONG"
    elif bias_mode == "BEAR":
        logging.info("🔁 Mapping Bias: BEAR → SHORT")

    persist_days = int(bias.get("persist_days", 0))
    bias_date   = bias.get("bias_date") or bias.get("anchor_friday") or datetime.now().strftime("%Y-%m-%d")
    granularity = (bias.get("granularity") or "unknown").lower()

    last_bias = (state.get("last_bias") or NEUTRAL_DEFAULT_MODE).upper()
    anchor_today = get_weekly_anchor().strftime("%Y-%m-%d")

    # ✅ Akzeptiere jeden Tag derselben W-FRI-Woche
    try:
        bias_in_same_week = (
            pd.Timestamp(bias_date).to_period("W-FRI")
            == pd.Timestamp(anchor_today).to_period("W-FRI")
        )
    except Exception:
        bias_in_same_week = False

    anchor_ok = (granularity == "weekly" and bias_in_same_week)

    if not anchor_ok:
        logging.warning(f"⚠️  Bias nicht auf aktuellen Weekly-Anker ({anchor_today}) ausgerichtet – Umschalten unterdrückt.")
        state["next_mode"] = last_bias
        return state

    # ----------- Hauptlogik -----------
    if bias_mode == "NEUTRAL":
        next_mode = NEUTRAL_DEFAULT_MODE
    else:
        threshold = THRESH_LONG_TO_SHORT if bias_mode == "SHORT" else THRESH_SHORT_TO_LONG
        if persist_days >= threshold:
            next_mode = bias_mode
            state["last_update"] = bias_date
            state["persist_days"] = 0
        else:
            next_mode = last_bias

    # ----------- Update State -----------
    state["next_mode"] = next_mode
    state["last_bias"] = next_mode if bias_mode != "NEUTRAL" else last_bias

    logging.info(
        f"Bias={bias_mode}, last_bias={last_bias}, persist_days={persist_days}, "
        f"thr=({THRESH_LONG_TO_SHORT}/{THRESH_SHORT_TO_LONG}), anchor_ok={anchor_ok} → next={next_mode}"
    )
    return state

# ──────────────────────────────────────────────
# Trader starten
# ──────────────────────────────────────────────
def launch_trader(script_name: str):
    """Startet den passenden Trader im Hintergrund und loggt in trader_cron.log."""
    py_bin = sys.executable
    trader_path = os.path.join(BASE, "trader", script_name)
    if not os.path.exists(trader_path):
        logging.error(f"❌ Trader-Skript nicht gefunden: {trader_path}")
        return

    os.makedirs(os.path.dirname(PATH_LOGRUN), exist_ok=True)
    try:
        with open(PATH_LOGRUN, "a", buffering=1) as lf:
            lf.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | INFO | ▶️ Starte {trader_path}\n")
            subprocess.Popen([py_bin, "-u", trader_path], stdout=lf, stderr=subprocess.STDOUT)
    except Exception as e:
        logging.error(f"❌ Konnte Trader nicht starten: {e}")

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    bias_info = load_market_bias("NASDAQ100")
    BIAS = bias_info.get("bias", "NEUTRAL").upper()
    print(f"📤 Market Bias gelesen → {BIAS} (L={bias_info.get('triple_long')}, S={bias_info.get('triple_short')})")

    bias  = load_json(PATH_BIAS, {})
    bias_source = "market_bias.json"

    # Fallback: falls aktuelle Datei fehlt → letztes Log aus Log_Files
    if not bias:
        latest = latest_bias_log()
        if latest:
            bias = load_json(latest, {})
            bias_source = os.path.basename(latest)
            logging.info(f"ℹ️  Verwende Bias aus Log-Datei: {bias_source}")

    if not bias:
        logging.error("❌ Kein Bias gefunden (weder market_bias.json noch Log_Files).")
        return

    state = load_json(PATH_STATE, {})
    state = decide_next_mode(bias, state)
    save_json(PATH_STATE, state)

    # 🧭 Overall-Regime-Integration
    overall = load_overall_regime()
    bias_mode = (bias.get("bias") or "NEUTRAL").upper()

    # 🧩 Mapping sicherstellen
    if bias_mode == "BULL":
        bias_mode = "LONG"
    elif bias_mode == "BEAR":
        bias_mode = "SHORT"

    if overall == "BEAR":
        script = "intraday_trader_short.py"
        note = "🔴 Overall-Regime=BEAR → Short-Trader aktiv"
    else:
        script = "intraday_trader_long.py"
        note = f"🟢 Overall-Regime={overall} → Long-Trader aktiv"

    if (overall == "BULL" and bias_mode == "SHORT") or (overall == "BEAR" and bias_mode == "LONG"):
        logging.warning(f"⚠️  Divergenz: Overall-Regime ({overall}) ≠ 5-3-Bias ({bias_mode})")

    logging.info(note)
    logging.info(f"🚀 Nächster Trader: {script}")

    # 🚀 Trader wirklich starten
    launch_trader(script)


if __name__ == "__main__":
    main()

