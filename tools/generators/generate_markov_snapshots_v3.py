#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import argparse


# ─────────────────────────────────────────────
# PATH PATCH (wie in deinem Stack)
# ─────────────────────────────────────────────
MARKOV_ROOT = Path(__file__).resolve().parents[2]  # .../Markov
if str(MARKOV_ROOT) not in sys.path:
    sys.path.insert(0, str(MARKOV_ROOT))

from tools.prices_eodhd import tool_prices  # dein Loader


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class SnapCfg:
    universe_name: str = "nasdaq100"
    out_dir: Path = MARKOV_ROOT / "data" / "snapshots"
    backtest_start: str = "2023-01-01"
    backtest_end: str = datetime.utcnow().date().isoformat()  # heute UTC
    warmup_years_min: int = 2
    warmup_years_max: int = 3

    # Frequenzen
    freqs: Tuple[str, ...] = ("weekly", "monthly")

    # Ranking / Spalten
    rank_by: str = "p_up"  # optional: "next_ret" wenn du das später ergänzt
    save_csv: bool = True


def load_universe(universe: str) -> List[str]:
    """
    Lädt Ticker eines Universums robust.
    Unterstützt:
    - eine Zeile mit kommagetrennten Tickern
    - mehrere Zeilen
    - Mischformen
    """

    paths: List[Path] = []

    # Markov-root relativ
    paths += [
        MARKOV_ROOT / "universes" / f"{universe}.txt",
        MARKOV_ROOT / "data" / "universes" / f"{universe}.txt",
        MARKOV_ROOT / "tools" / "universes" / f"{universe}.txt",
    ]

    # Global Python_for_Finance/universes
    pff_root = MARKOV_ROOT.parent
    paths += [
        pff_root / "universes" / f"{universe}.txt",
    ]

    for p in paths:
        if not p.exists():
            continue

        raw = p.read_text().strip()
        if not raw:
            continue

        tickers: List[str] = []
        for line in raw.splitlines():
            for tk in line.split(","):
                tk = tk.strip().upper()
                if tk:
                    tickers.append(tk)

        # Duplikate entfernen, Reihenfolge behalten
        seen = set()
        uniq: List[str] = []
        for tk in tickers:
            if tk not in seen:
                uniq.append(tk)
                seen.add(tk)

        if len(uniq) == 0:
            raise RuntimeError(f"Universe-Datei leer oder unlesbar: {p}")

        print(f"✅ Universe '{universe}' geladen aus {p} ({len(uniq)} Ticker)")
        return uniq

    raise FileNotFoundError(
        f"Universe '{universe}' nicht gefunden. Erwartete z.B.:\n"
        f"  {pff_root / 'universes' / f'{universe}.txt'}"
    )




def _rebalance_dates_from_any_series(px_any: pd.Series, freq: str) -> pd.DatetimeIndex:
    px_any = px_any.dropna()
    if freq == "weekly":
        return px_any.resample("W-FRI").last().index
    if freq == "monthly":
        return px_any.resample("M").last().index
    raise ValueError("freq muss weekly|monthly sein")


def _compute_warmup_start(backtest_start: str, years: int) -> str:
    dt0 = pd.to_datetime(backtest_start)
    warm = dt0 - pd.DateOffset(years=years)
    return warm.date().isoformat()


# ─────────────────────────────────────────────
# Markov-core-v3 Adapter
# ─────────────────────────────────────────────

def _p_up_from_prices_markov_v3(
    prices: pd.Series | pd.DataFrame,
    freq: str = "weekly"
) -> float:
    """
    Korrekte Anbindung an markov_core_v3:
    - preprocess_prices
    - calc_transitions
    - letzter p_up-Wert der Serie
    """
    try:
        import tools.markov_core_v3 as mc3

        # Preise robust in DataFrame mit Close bringen
        if isinstance(prices, pd.Series):
            df = prices.to_frame("Close")
        else:
            df = prices.copy()

        if df is None or df.empty:
            return np.nan

        # 1️⃣ Resampling / Cleaning
        df_prep = mc3.preprocess_prices(df, freq=freq)
        if df_prep is None or df_prep.empty or len(df_prep) < 10:
            return np.nan

        # 2️⃣ Markov Transitions
        _, p_up_series = mc3.calc_transitions(df_prep)
        if p_up_series is None or p_up_series.empty:
            return np.nan

        # 3️⃣ Snapshot = letzter Wert
        return float(p_up_series.iloc[-1])

    except Exception as e:
        # Optional: Debug
        # print(f"p_up error: {e}")
        return np.nan

# ─────────────────────────────────────────────
# Snapshot Engine
# ─────────────────────────────────────────────

def _build_snapshot_for_date(
    prices_by_ticker: Dict[str, Optional[pd.Series]],
    as_of: pd.Timestamp,
    freq: str,
) -> pd.DataFrame:
    """
    Berechnet p_up je Ticker aus vorab geladenen Preisen (kein Look-Ahead).
    """
    rows = []

    for tk, full_px in prices_by_ticker.items():
        if full_px is None or full_px.empty:
            p_up = np.nan
        else:
            px_slice = full_px.loc[:as_of]
            p_up = _p_up_from_prices_markov_v3(px_slice, freq=freq)

        rows.append({
            "date": as_of,
            "Ticker": tk,
            "p_up": p_up,
        })

    df = pd.DataFrame(rows).set_index("date")
    df["p_up"] = pd.to_numeric(df["p_up"], errors="coerce")
    df["rank"] = df["p_up"].rank(ascending=False, method="min")
    return df


def generate_snapshots(cfg: SnapCfg) -> Dict[str, pd.DataFrame]:
    tickers = load_universe(cfg.universe_name)
    print(f"📦 Universe size: {len(tickers)}")

    assert all("," not in tk for tk in tickers), "Universe enthält noch Kommas – Parsing fehlgeschlagen"

    # Warmup: erst max3Y versuchen, wenn zu wenig Daten -> min2Y
    warm3 = _compute_warmup_start(cfg.backtest_start, cfg.warmup_years_max)
    warm2 = _compute_warmup_start(cfg.backtest_start, cfg.warmup_years_min)

    # Rebalance-Kalender brauchen wir aus irgendeinem "stabilen" Ticker
    # (hier: NDX Proxy, ansonsten erster Ticker)
    probe_ticker = tickers[0]
    probe = tool_prices(probe_ticker, start=warm3, end=cfg.backtest_end)
    if isinstance(probe, pd.DataFrame):
        col = "adjclose" if "adjclose" in probe.columns else probe.columns[-1]
        probe = probe[col]
    probe.index = pd.to_datetime(probe.index)
    probe = probe.sort_index()

    # Rebalance Dates aus Probe erstellen und auf Backtest-Fenster schneiden
    out: Dict[str, pd.DataFrame] = {}
    bt_start = pd.to_datetime(cfg.backtest_start)
    bt_end = pd.to_datetime(cfg.backtest_end)

    for freq in cfg.freqs:
        rbd = _rebalance_dates_from_any_series(probe, freq=freq)
        rbd = rbd[(rbd >= bt_start) & (rbd <= bt_end)]
        if len(rbd) == 0:
            raise RuntimeError(f"Keine Rebalance-Daten für {freq} im Fenster {cfg.backtest_start}..{cfg.backtest_end}")

        # Warmup-Fallback: wenn Probe im 3Y-Warmup zu kurz ist, nimm 2Y
        warmup_start = warm3
        if probe.loc[:bt_start].dropna().shape[0] < 400:  # grob: ~1.5y daily bars
            warmup_start = warm2

        # ─────────────────────────────────────────────
        # 🚀 SPEED PATCH: Preise einmal pro Ticker laden
        # ─────────────────────────────────────────────
        print("📥 Preloading prices per ticker …")
        prices_by_ticker: Dict[str, Optional[pd.Series]] = {}

        for tk in tickers:
            try:
                px = tool_prices(tk, start=warmup_start, end=cfg.backtest_end)

                if isinstance(px, pd.DataFrame):
                    for c in ["adjclose", "Adj Close", "adjusted_close", "close", "Close"]:
                        if c in px.columns:
                            px = px[c]
                            break
                    else:
                        px = px.iloc[:, -1]

                px.index = pd.to_datetime(px.index)
                prices_by_ticker[tk] = px.sort_index()

            except Exception:
                prices_by_ticker[tk] = None

        # ─────────────────────────────────────────────
        # Snapshot Loop (jetzt NUR noch slicing)
        # ─────────────────────────────────────────────
        snaps = []
        for d in rbd:
            print(f"📌 {freq.upper()} snapshot @ {d.date()} (warmup_start={warmup_start})")
            snaps.append(
                _build_snapshot_for_date(
                    prices_by_ticker,
                    as_of=d,
                    freq=freq
                )
            )

            
        df_freq = pd.concat(snaps).sort_index()
        out[freq] = df_freq

        # save
        cfg.out_dir.mkdir(parents=True, exist_ok=True)
        if cfg.save_csv:
            fp = cfg.out_dir / f"snapshots_{cfg.universe_name}_{freq}.csv"
            df_freq.to_csv(fp, index=True)
            print(f"✅ saved: {fp}")

    return out

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", type=str, default="nasdaq100")
    args = parser.parse_args()

    UNIVERSE = args.universe.lower()

    cfg = SnapCfg(
        universe_name=UNIVERSE,
        out_dir=MARKOV_ROOT / "data" / "snapshots" / UNIVERSE,
        backtest_start="2023-01-01",
        backtest_end=datetime.utcnow().date().isoformat(),
        warmup_years_min=2,
        warmup_years_max=3,
        freqs=("weekly",),
    )

    generate_snapshots(cfg)


