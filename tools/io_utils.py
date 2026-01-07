#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os, json, logging

def load_api_key(path: str) -> str | None:
    try:
        return open(os.path.expanduser(path)).read().strip()
    except FileNotFoundError:
        logging.error(f"API-Key file not found: {path}")
        return None

def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def setup_logging(verbose=False):
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s")

