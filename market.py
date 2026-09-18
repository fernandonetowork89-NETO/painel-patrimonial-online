
import os
from datetime import datetime
import requests
import streamlit as st


def brapi_token():
    try:
        return str(st.secrets.get("BRAPI_TOKEN", "")).strip()
    except Exception:
        return ""


def _chunks(items, n=20):
    for i in range(0, len(items), n):
        yield items[i:i+n]


@st.cache_data(ttl=1800, show_spinner=False)
def get_quotes(tickers_tuple):
    tickers = sorted({str(x).strip().upper() for x in tickers_tuple if str(x).strip()})
    if not tickers:
        return {}

    token = brapi_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    result = {}

    for chunk in _chunks(tickers, 20):
        url = "https://brapi.dev/api/quote/" + ",".join(chunk)
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        payload = resp.json()

        for item in payload.get("results", []):
            ticker = str(item.get("symbol", "")).upper()
            price = item.get("regularMarketPrice")
            if ticker and price is not None:
                result[ticker] = {
                    "price": float(price),
                    "change_pct": float(item.get("regularMarketChangePercent") or 0),
                    "name": item.get("shortName") or ticker,
                    "updated_at": payload.get("requestedAt") or datetime.now().isoformat(),
                }

    return result
