#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
from pathlib import Path

from tools.alpha_backtracker_standalone import (
    alphalyzer_backtest_standalone,
    compute_turnover,
    split_train_test
)

GLOBAL_START = "2018-01-01"


def run_alpha_grid_search(
    universe_file: Path,
    freqs=("weekly", "monthly"),
    top_n_range=range(1, 11),
    split_year="2023-01-01"
):

    results = []

    for freq in freqs:
        for n in top_n_range:

            try:
                nav, hist, metrics_all = alphalyzer_backtest_standalone(
                    universe_file=universe_file,
                    freq=freq,
                    top_n=n
                )

                train_m, test_m = split_train_test(nav, split_year=split_year)
                turnover = compute_turnover(hist)

                results.append({
                    "freq": freq,
                    "top_n": n,

                    # Gesamt
                    "Sharpe_ALL": metrics_all["Sharpe"],
                    "CAGR_ALL": metrics_all["CAGR"],
                    "MaxDD_ALL": metrics_all["MaxDD"],

                    # Train
                    "Sharpe_TRAIN": train_m["Sharpe"],
                    "CAGR_TRAIN": train_m["CAGR"],

                    # Test (OOS!)
                    "Sharpe_TEST": test_m["Sharpe"],
                    "CAGR_TEST": test_m["CAGR"],
                    "MaxDD_TEST": test_m["MaxDD"],

                    "Turnover": turnover
                })

            except Exception as e:
                print(f"❌ Fehler bei {freq} / Top-{n}: {e}")

    df = pd.DataFrame(results)

    # ✅ Ranking auf echtem Out-of-Sample
    df["rank_test"] = df["Sharpe_TEST"].rank(ascending=False)
    df = df.sort_values("rank_test").reset_index(drop=True)

    return df

