#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
from sklearn.cluster import KMeans

def assign_bracket(p_up, brackets=5):
    """
    Ordnet einen p_up-Wert einem Bracket (1 bis `brackets`) zu.
    - p_up: float zwischen 0 und 1
    - brackets: Anzahl der Brackets (default 5)
    
    Rückgabe: int Bracket von 1 (niedrig) bis brackets (hoch)
    """
    if p_up is None or np.isnan(p_up):
        return 0  # kein gültiger Wert
    # Skaliere p_up auf 0..brackets
    scaled = int(np.floor(p_up * brackets)) + 1
    return min(max(scaled, 1), brackets)

def create_clusters(values, n_clusters=3):
    """
    Clustert eine Liste von Werten mit KMeans.
    
    Args:
        values (list oder np.array): 1D-Liste oder Array von Zahlen
        n_clusters (int): Anzahl Cluster (default 3)
    
    Rückgabe:
        Liste von Clusterlabels (gleiche Länge wie input)
    """
    if len(values) == 0:
        return []

    X = np.array(values).reshape(-1, 1)
    km = KMeans(n_clusters=n_clusters, random_state=42)
    km.fit(X)
    return km.labels_.tolist()

