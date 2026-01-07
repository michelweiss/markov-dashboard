#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from pandas_datareader import data as pdr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "economics" / "data"
DATA_DIR.mkdir(exist_ok=True)

OUT_FILE = DATA_DIR / "macro_actuals.csv"


def download_cpi_actuals(start="2000-01-01"):
    cpi = pdr.DataReader("CPIAUCSL", "fred", start)
    cpi["cpi_yoy"] = cpi["CPIAUCSL"].pct_change(12, fill_method=None) * 100
    df = cpi.dropna().reset_index().rename(columns={"DATE": "date"})
    df["event"] = "US CPI"
    df["actual"] = df["cpi_yoy"]
    df["consensus"] = df["actual"].shift(1)
    df["surprise"] = df["actual"] - df["consensus"]
    return df.dropna()[["date", "event", "actual", "consensus", "surprise"]]


def download_nfp_actuals(start="2000-01-01"):
    nfp = pdr.DataReader("PAYEMS", "fred", start)
    nfp["jobs_change"] = nfp["PAYEMS"].diff()
    df = nfp.dropna().reset_index().rename(columns={"DATE": "date"})
    df["event"] = "US NFP"
    df["actual"] = df["jobs_change"]
    df["consensus"] = df["actual"].shift(1)
    df["surprise"] = df["actual"] - df["consensus"]
    return df.dropna()[["date", "event", "actual", "consensus", "surprise"]]


def download_gdp_actuals(start="2000-01-01"):
    gdp = pdr.DataReader("GDPC1", "fred", start)  # quarterly real GDP
    df = gdp.dropna().reset_index().rename(columns={"DATE": "date"})
    df["gdp"] = df["GDPC1"]

    # QoQ annualized %
    df["actual"] = ((df["gdp"] / df["gdp"].shift(1)) ** 4 - 1) * 100

    df["event"] = "US GDP"
    df["consensus"] = df["actual"].shift(1)      # proxy
    df["surprise"]  = df["actual"] - df["consensus"]

    return df.dropna()[["date", "event", "actual", "consensus", "surprise"]]


def download_fomc_decisions(start="2000-01-01"):
    # Upper bound target rate (daily)
    taru = pdr.DataReader("DFEDTARU", "fred", start)
    df = taru.dropna().reset_index().rename(columns={"DATE": "date"})
    df["event"] = "FOMC"
    df.rename(columns={"DFEDTARU": "actual"}, inplace=True)

    # "consensus" hier: previous target (naiv) -> surprise = change
    df["consensus"] = df["actual"].shift(1)
    df["surprise"] = df["actual"] - df["consensus"]

    return df.dropna()[["date", "event", "actual", "consensus", "surprise"]]
    

def download_eu_cpi_actuals(start="2000-01-01"):
    hicp = pdr.DataReader("CP0000EZ19M086NEST", "fred", start)
    hicp["actual"] = hicp.iloc[:, 0]

    df = hicp.dropna().reset_index()
    df.rename(columns={"DATE": "date"}, inplace=True)

    df["event"] = "EU CPI"
    df["consensus"] = df["actual"].shift(1)
    df["surprise"] = df["actual"] - df["consensus"]

    return df.dropna()[["date", "event", "actual", "consensus", "surprise"]]



def download_eu_gdp_actuals(start="2000-01-01"):
    gdp = pdr.DataReader("CLVMEURSCAB1GQEA19", "fred", start)
    gdp["actual"] = gdp.iloc[:, 0]

    df = gdp.dropna().reset_index()
    df.rename(columns={"DATE": "date"}, inplace=True)

    df["event"] = "EU GDP"
    df["consensus"] = df["actual"].shift(1)
    df["surprise"] = df["actual"] - df["consensus"]

    return df.dropna()[["date", "event", "actual", "consensus", "surprise"]]


def download_snb_decisions(start="2000-01-01"):
    """
    Swiss National Bank policy rate decisions
    Source: FRED (IRSTCI01CHM156N)
    """

    snb = pdr.DataReader("IRSTCI01CHM156N", "fred", start)

    df = (
        snb
        .dropna()
        .reset_index()
        .rename(columns={"DATE": "date", "IRSTCI01CHM156N": "actual"})
    )

    df["event"] = "SNB"

    # Consensus = previous decision (same logic as FOMC / ECB)
    df["consensus"] = df["actual"].shift(1)
    df["surprise"]  = df["actual"] - df["consensus"]

    return df.dropna()[["date", "event", "actual", "consensus", "surprise"]]


def download_ch_cpi_actuals(start="2000-01-01"):
    # Switzerland CPI index (COICOP 1999 total)
    df = pdr.DataReader("CHECPIALLMINMEI", "fred", start)
    df["actual"] = df.iloc[:, 0]

    df = df.dropna().reset_index().rename(columns={"DATE": "date"})
    df["event"] = "CH CPI"
    df["consensus"] = df["actual"].shift(1)
    df["surprise"]  = df["actual"] - df["consensus"]

    return df.dropna()[["date", "event", "actual", "consensus", "surprise"]]
    

def download_ch_gdp_actuals(start="2000-01-01"):
    # Switzerland real GDP (seasonally adjusted)
    gdp = pdr.DataReader("CLVMNACSAB1GQCH", "fred", start)

    df = gdp.dropna().reset_index().rename(columns={"DATE": "date"})
    df["gdp"] = df["CLVMNACSAB1GQCH"]

    # QoQ annualized % (match US-style metric)
    df["actual"] = ((df["gdp"] / df["gdp"].shift(1)) ** 4 - 1) * 100

    df["event"] = "CH GDP"
    df["consensus"] = df["actual"].shift(1)
    df["surprise"]  = df["actual"] - df["consensus"]

    return df.dropna()[["date", "event", "actual", "consensus", "surprise"]]


def load_snb_actuals():
    df = pd.read_csv(DATA_DIR / "snb_policy_rate.csv", parse_dates=["date"])
    df = df.sort_values("date")

    df["event"] = "SNB"
    df["consensus"] = df["actual"].shift(1)
    df["surprise"]  = df["actual"] - df["consensus"]

    return df.dropna()[["date","event","actual","consensus","surprise"]]



def build_macro_actuals():
    cpi   = download_cpi_actuals()
    nfp   = download_nfp_actuals()
    gdp   = download_gdp_actuals()
    fomc  = download_fomc_decisions()

    eu_cpi = download_eu_cpi_actuals()
    eu_gdp = download_eu_gdp_actuals()

    ch_cpi = download_ch_cpi_actuals()
    ch_gdp = download_ch_gdp_actuals()

    ecb = pd.read_csv(DATA_DIR / "ecb_decisions.csv", parse_dates=["date"])
    snb = download_snb_decisions()

    out = pd.concat(
        [cpi, nfp, gdp, fomc,
         eu_cpi, eu_gdp,
         ch_cpi, ch_gdp,
         ecb, snb],
        ignore_index=True
    )

    out = out.sort_values(["event", "date"]).reset_index(drop=True)
    out.to_csv(OUT_FILE, index=False)

    print(f"✔ Macro actuals written: {OUT_FILE}")



if __name__ == "__main__":
    build_macro_actuals()

