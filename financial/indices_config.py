#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# -*- coding: utf-8 -*-
"""
Equity Indices Configuration
----------------------------
Single Source of Truth for Financial / Equity Probabilities
"""

INDICES = {
    "usa_tech": {
        "label": "USA – Nasdaq 100",
        "ticker": "NDX.INDX",
        "region": "USA",
    },
    "usa_broad": {
        "label": "USA – S&P 500",
        "ticker": "GSPC.INDX",
        "region": "USA",
    },
    "europe": {
        "label": "Europe – EURO STOXX 50",
        "ticker": "SX5E.INDX",
        "region": "Europe",
    },
    "switzerland": {
        "label": "Switzerland – SMI",
        "ticker": "SSMI.INDX",
        "region": "Switzerland",
    },
    "japan": {
        "label": "Japan – Nikkei 225",
        "ticker": "N225.INDX",
        "region": "Japan",
    },
}

