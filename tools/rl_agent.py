#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np, random, pandas as pd

def train_q_learning(df, features, target="next_ret", n_bins=4, alpha=0.1, gamma=0.95, epsilon=0.2):
    for col in features:
        if col != "Cluster":
            df[col+"_bin"] = pd.qcut(df[col], q=n_bins, labels=False, duplicates='drop')
    df["Cluster_bin"] = df["Cluster"].astype(int) if "Cluster" in df else 0
    state_cols = [c+"_bin" for c in features if c!="Cluster"] + ["Cluster_bin"]
    df["state"] = list(zip(*[df[c] for c in state_cols]))
    actions = [0,1]
    Q = {s:{a:0.0 for a in actions} for s in df["state"].unique()}
    for _ in range(50):
        for _, row in df.iterrows():
            s=row["state"]
            a=random.choice(actions) if np.random.rand()<epsilon else max(Q[s],key=Q[s].get)
            r=row[target] if a==1 else 0
            Q[s][a]+=alpha*(r+gamma*max(Q[s].values())-Q[s][a])
    df["action"]=df["state"].map(lambda s:max(Q[s],key=Q[s].get))
    df["reward"]=df.apply(lambda r:r[target] if r["action"]==1 else 0,axis=1)
    return df, Q

