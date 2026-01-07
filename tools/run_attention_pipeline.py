#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from pathlib import Path
import subprocess

MARKOV_ROOT = Path(__file__).resolve().parents[1]
TOOLS = MARKOV_ROOT / "tools"

def run_pipeline(universe: str):
    """
    universe = 'nasdaq100', 'world', ...
    """
    print(f"🚀 Running pipeline for universe: {universe}")

    # 1️⃣ Generate snapshots
    subprocess.run(
        ["python3", "generate_markov_snapshots_v3.py", "--universe", universe],
        cwd=TOOLS
    )

    # 2️⃣ Weekly Attention
    subprocess.run(
        ["python3", "analyze_attention_weekly.py", "--universe", universe],
        cwd=TOOLS
    )

    # 3️⃣ Stress Response (T1_core)
    subprocess.run(
        ["python3", "stress_response_markov.py", "--universe", universe],
        cwd=TOOLS
    )

    # 4️⃣ Stress-adjusted Score
    subprocess.run(
        ["python3", "attention_stress_score.py", "--universe", universe],
        cwd=TOOLS
    )

