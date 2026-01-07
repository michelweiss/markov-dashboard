#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np, pandas as pd

def fuse_p_up(df, vr_col="VR", thr_mom=1.05, thr_mr=0.95):
    if df.empty: return df
    w_def, w_mom, w_mr, w_neu = (0.5,0.3,0.2), (0.6,0.3,0.1), (0.3,0.4,0.3), (0.4,0.4,0.2)
    def w(row):
        vr = row.get(vr_col, np.nan)
        if np.isnan(vr): return w_def
        if vr>thr_mom: return w_mom
        if vr<thr_mr: return w_mr
        return w_neu
    weights = np.vstack([w(r) for _,r in df.iterrows()])
    d,w,m = (df.get("p_up_daily", np.nan), df.get("p_up_week", np.nan), df.get("p_up_month", np.nan))
    vals = np.vstack([d,w,m]).T
    df["p_up_meta"] = np.einsum("ij,ij->i", weights, vals)
    return df

