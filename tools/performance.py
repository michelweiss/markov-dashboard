#!/usr/bin/env python
# coding: utf-8

# In[ ]:


"""
Dieses Modul enthält eine Hilfsfunktion für die Performance-Berechnung dynamischer, periodisch neu gewichteter Portfolios.

Verwende es als eigenständiges Modul (performance.py) und importiere:
```python
from performance import compute_dynamic_portfolio_performance
```
"""
import pandas as pd
import numpy as np

def compute_dynamic_portfolio_performance(price_data: dict,
                                          screen_dates: list,
                                          screens: dict,
                                          freq='D'):
    """
    Berechnet Portfolio-Performance für dynamisch rebalancierte Screenings.

    Args:
      price_data: Dict[Ticker -> DataFrame mit 'Close' und DatetimeIndex]
      screen_dates: Sortierte Liste von Rebalance-Daten (date-Objekte)
      screens: Dict[date -> List[Ticker]] für jedes Screening-Datum
      freq: 'D','W' oder 'M'

    Returns:
      portfolio_df: DataFrame der Portfolio-Schlusskurse
      returns_df: DataFrame der Portfolio-Renditen
      metrics: Dict mit Cum%, Ann%, Vol%, Sharpe
    """
    portfolio_values = []

    for i in range(len(screen_dates) - 1):
        start = screen_dates[i]
        end = screen_dates[i + 1]
        tickers = screens.get(start, [])
        if not tickers:
            continue

        dfs = []
        for tk in tickers:
            df = price_data.get(tk)
            if df is None or df.empty:
                continue
            dfs.append(df[['Close']].loc[start:end].rename(columns={'Close': tk}))
        if not dfs:
            continue

        prices = pd.concat(dfs, axis=1).dropna(how='any')
        if prices.empty:
            continue
        weights = np.repeat(1 / prices.shape[1], prices.shape[1])
        portfolio = prices.dot(weights)
        portfolio_values.append(portfolio)

    if not portfolio_values:
        # Keine Perioden gebildet
        empty = pd.DataFrame()
        return empty, empty, {'Cum%': np.nan, 'Ann%': np.nan, 'Vol%': np.nan, 'Sharpe': np.nan}

    all_port = pd.concat(portfolio_values)
    all_port = all_port[~all_port.index.duplicated(keep='first')].sort_index()
    ret = all_port.pct_change().dropna()

    cum_return = (all_port.iloc[-1] / all_port.iloc[0] - 1) * 100
    years = (all_port.index[-1] - all_port.index[0]).days / 365.25
    ann_return = ((1 + cum_return / 100) ** (1 / years) - 1) * 100 if years else np.nan
    scale = {'D': 252, 'W': 52, 'M': 12}.get(freq.upper(), 252)
    vol = ret.std() * np.sqrt(scale) * 100
    sharpe = ann_return / vol if vol else np.nan

    metrics = {
        'Cum%': round(cum_return, 2),
        'Ann%': round(ann_return, 2),
        'Vol%': round(vol, 2),
        'Sharpe': round(sharpe, 2)
    }

    return all_port.to_frame(name='Portfolio'), ret.to_frame(name='Returns'), metrics

