#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# 🩺  Markov System – Morning Health Check
# ============================================================
# Prüft, ob alle Nacht-/Abend-Jobs (Trader, Bias, p_up Tester)
# erfolgreich gelaufen sind.
# Ergebnis: kompakte Übersicht mit OK / WARN / ERROR.
# ============================================================

import os, re, json
from datetime import datetime, timedelta

# ── Basispfade ───────────────────────────────────────────────
BASE = os.path.expanduser("~/Documents/Python_for_Finance/Markov")
LOGS = {
    "Trader": os.path.join(BASE, "trader_cron.log"),
    "p_up Live": os.path.join(BASE, "p_up_live.log"),
    "Weekly Screener": os.path.join(BASE, "trader.log"),
    "Monthly": os.path.join(BASE, "fusion_monthly.log"),  # ✅ liegt im Root!
}
SNAP_JSON = os.path.join(BASE, "highlow_monitor.json")

NOW = datetime.now()
YEST = NOW - timedelta(days=1)
IS_WEEKEND = NOW.weekday() >= 5  # Samstag=5, Sonntag=6

# ── Funktionen ───────────────────────────────────────────────
def read_tail(path, n=200):
    """Liest die letzten Zeilen einer Logdatei."""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return "".join(f.readlines()[-n:])

def check_log(name, path):
    txt = read_tail(path)
    if not txt:
        return (name, "❌", "Fehlt oder leer")

    # Zeitprüfung
    m = re.findall(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", txt)
    if m:
        last = datetime.strptime(m[-1], "%Y-%m-%d %H:%M:%S")
        if last < YEST:
            return (name, "⚠️", f"letzter Eintrag alt ({last})")

    # Keyword-Prüfung
    if "ERROR" in txt or "Traceback" in txt:
        return (name, "❌", "Fehler im Log erkannt")
    if "🚀" in txt or "💾" in txt or "Bias" in txt:
        return (name, "✅", "ok")
    return (name, "⚠️", "keine Aktivität erkannt")

def check_json(path):
    if not os.path.exists(path):
        return ("High/Low Snapshot", "❌", "Datei fehlt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        date = data.get("date")
        hs, ls = data.get("high_share"), data.get("low_share")

        if not date:
            return ("High/Low Snapshot", "❌", "kein Datumsfeld gefunden")

        # Wochenend-Ausnahme: Freitag bleibt gültig
        today_str = NOW.strftime("%Y-%m-%d")
        if IS_WEEKEND:
            weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
            if weekday == 4:  # Freitag
                return ("High/Low Snapshot", "✅", f"ok (Freitag {date}, high={hs:.3f}, low={ls:.3f})")

        if date != today_str:
            return ("High/Low Snapshot", "⚠️", f"nicht aktuell ({date})")

        return ("High/Low Snapshot", "✅", f"high={hs:.3f}, low={ls:.3f}")
    except Exception as e:
        return ("High/Low Snapshot", "❌", f"Lesefehler: {e}")

# ── Checks ausführen ─────────────────────────────────────────
results = [check_log(name, path) for name, path in LOGS.items()]
results.append(check_json(SNAP_JSON))

# ── Ausgabe ──────────────────────────────────────────────────
print("🩺 MARKOV SYSTEM – MORNING HEALTH CHECK\n")
for name, status, info in results:
    print(f"{status:3} {name:20s} → {info}")
print("\nZeitpunkt:", NOW.strftime("%Y-%m-%d %H:%M:%S"))

# Exitcode (optional für Cron-Benachrichtigung)
if any(s[1] == "❌" for s in results):
    exit(1)

