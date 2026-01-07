#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# -*- coding: utf-8 -*-
"""
VIX Configuration
-----------------
Single Source of Truth for Financial / Volatility Probabilities
"""

VIX = {
    "usa_vix_inv": {
        "label": "USA – VIX (inverted)",
        "region": "USA",
        "ticker": "VIX.INDX",
        "transform": "neg_log",   # Dokumentation: vix_inv = -log(VIX)
    },
}

