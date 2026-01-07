#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import pandas as pd

from tools.markov_core_v1 import calc_transitions

def optimize_threshold_vectorized(df, thr_grid=None):
    """
    Vektorisierte Threshold-Optimierung.
    Erwartet df mit:
      - 'Returns'
      - 'y_bin'
    """

    if thr_grid is None:
        thr_grid = np.linspace(0.3, 0.7, 21)

    if len(df) < 30:
        return 0.5

    trans = calc_transitions(df)
    y = df["y_bin"].to_numpy()
    ret = df["Returns"].to_numpy()

    idx = np.arange(2, len(df) - 1)
    if idx.size == 0:
        return 0.5

    states = (y[idx - 2] << 2) | (y[idx - 1] << 1) | y[idx]

    P = np.array([
        trans.get((a, b, c), {}).get("1", 0.5)
        for a in (0, 1)
        for b in (0, 1)
        for c in (0, 1)
    ])

    p_up = P[states]
    fwd_ret = ret[idx + 1]

    mask = p_up[:, None] >= thr_grid[None, :]
    strat = np.where(mask, fwd_ret[:, None], -fwd_ret[:, None])

    perf = np.nanmean(strat, axis=0)

    if np.all(np.isnan(perf)):
        return 0.5

    return float(thr_grid[np.nanargmax(perf)])

def compute_p_up(df, trans=None):
    """
    Berechnet p_up für den letzten Tag im DataFrame.

    Args:
        df (pd.DataFrame): Mit ['y_bin'] und min. 3 Zeilen.
        trans (dict, optional): Vorab berechnete Transition-Matrix.

    Returns:
        float: p_up oder np.nan.
    """
    if trans is None:
        trans = calc_transitions(df)

    last_idx = len(df) - 1
    y_prev2 = int(df['y_bin'].iat[last_idx - 2])
    y_prev1 = int(df['y_bin'].iat[last_idx - 1])
    y_today = int(df['y_bin'].iat[last_idx])

    return trans.get((y_prev2, y_prev1, y_today), {}).get('1', np.nan)

