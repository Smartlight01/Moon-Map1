# ---------------------------------------------------------
# MUST BE FIRST — Future import
# ---------------------------------------------------------
from __future__ import annotations

# ---------------------------------------------------------
# Imports
# ---------------------------------------------------------
import streamlit as st
import os
import json as _json
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, time
from pathlib import Path as _Path

try:
    from zoneinfo import ZoneInfo as _ZoneInfo
except:
    from pytz import timezone as _ZoneInfo

# Internal modules
import config
from discord_oauth import (
    get_authorize_url,
    exchange_code,
    get_user,
    get_member,
    user_has_role
)

from data_provider import get_spot
from scanner import fetch_chain, compute_net_tables
from gex_vex_ui import css, combined
from news_api import fetch_company_news_cards


# ---------------------------------------------------------
# AUTH STATE
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "discord_user" not in st.session_state:
    st.session_state.discord_user = None


# ---------------------------------------------------------
# DISCORD AUTH WALL
# ---------------------------------------------------------
def auth_wall():
    st.markdown("## 🔒 MoonWalkers Only")
    st.write(
        """
        This dashboard is **exclusive for verified MoonWalkers**  
        who hold the correct Discord role.
        """
    )

    login_url = get_authorize_url()
    st.link_button("Login with Discord", login_url)

    st.stop()


# ---------------------------------------------------------
# Handle OAuth Redirect (?code=...)
# ---------------------------------------------------------
params = st.experimental_get_query_params()

if not st.session_state.authenticated:

    if "code" in params:
        code = params["code"][0]

        token = exchange_code(code)
        user = get_user(token)
        member = get_member(token)

        if user_has_role(member, config.DISCORD_ROLE_ID):
            st.session_state.authenticated = True
            st.session_state.discord_user = user

            # Remove ?code= from URL
            st.experimental_set_query_params()
        else:
            st.error("⛔ You do not have the required Discord role.")
            st.stop()
    else:
        auth_wall()


# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="Moon Map", page_icon="🌙", layout="wide")
css()  # Apply the UI stylesheet


# ---------------------------------------------------------
# MAIN HEADER
# ---------------------------------------------------------
st.markdown(
    "<h1 style='text-align:center;'>🌙 Moon Map</h1>",
    unsafe_allow_html=True
)

st.success(f"Logged in as **{st.session_state.discord_user['username']}**")


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
_ET = _ZoneInfo("America/New_York")
_SNAP_DIR = _Path(".cache/snapshots")
_SNAP_DIR.mkdir(parents=True, exist_ok=True)


def _snap_path(symbol: str) -> _Path:
    safe = ''.join([c for c in symbol if c.isalnum() or c in ('_','-')])[:24]
    return _SNAP_DIR / f"{safe}.json"


def _now_et() -> datetime:
    return datetime.now(_ET)


def _premarket_freeze_active(now: datetime) -> bool:
    return time(0, 0) <= now.time() < time(9, 30)


def _save_snapshot(symbol: str, spot, raw_df):
    try:
        if raw_df is None or getattr(raw_df, 'empty', True):
            return
        payload = {
            'ts': _now_et().isoformat(),
            'spot': float(spot) if spot is not None else None,
            'columns': list(raw_df.columns),
            'records': raw_df.to_dict(orient='records'),
        }
        _snap_path(symbol).write_text(_json.dumps(payload))
    except:
        pass


def _load_snapshot(symbol: str):
    p = _snap_path(symbol)
    if not p.exists():
        return None, None
    try:
        obj = _json.loads(p.read_text())
        df = pd.DataFrame(obj.get('records') or [], columns=obj.get('columns') or None)
        return obj.get('spot'), df
    except:
        return None, None


@st.cache_data(ttl=180, show_spinner=False)
def rt_quote(sym: str):
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": sym, "token": config.FINNHUB_TOKEN},
            timeout=6
        )
        j = r.json() if r.ok else {}
        return (
            float(j.get("c", 0)),
            float(j.get("pc", 0)),
            float(j.get("d", 0)),
            float(j.get("dp", 0)),
        )
    except:
        return None, None, None, None


# ---------------------------------------------------------
# UI — TICKER INPUT
# ---------------------------------------------------------
symbol = st.text_input("Ticker", value="SPY").strip().upper()


# ---------------------------------------------------------
# REAL-TIME QUOTE + DATA
# ---------------------------------------------------------
rt_spot, rt_prev, chg, chg_pct = rt_quote(symbol)

company_info = yf.Ticker(symbol).get_info()


# ---------------------------------------------------------
# INFO CARDS UI
# ---------------------------------------------------------
colA, colB, colC, colD, colE, colF = st.columns(6)

with colA:
    st.metric("Price", f"{rt_spot:,.2f}" if rt_spot else "—", f"{chg:+.2f} ({chg_pct:+.2f}%)")

with colB:
    st.metric("Volume", f"{company_info.get('volume', 0):,}")

with colC:
    st.metric("Beta", company_info.get("beta") or "—")

with colD:
    st.metric("1y Target Est", company_info.get("targetMeanPrice") or "—")

with colE:
    st.metric("Short Float %", company_info.get("shortPercentOfFloat") or "—")

with colF:
    st.metric("Earnings", company_info.get("earningsTimestampStart") or "—")

st.divider()


# ---------------------------------------------------------
# OPTIONS DATA
# ---------------------------------------------------------
try:
    live_spot, live_raw = fetch_chain(symbol)
except:
    live_spot, live_raw = None, pd.DataFrame()

now = _now_et()

if _premarket_freeze_active(now):
    snap_spot, snap_raw = _load_snapshot(symbol)
    if snap_raw is not None:
        spot, raw = snap_spot or live_spot, snap_raw
    else:
        spot, raw = live_spot, live_raw
else:
    spot, raw = live_spot, live_raw

if raw is None or raw.empty:
    st.error("Could not fetch options chain for this symbol.")
    st.stop()

gex, vex, S = compute_net_tables(raw)


# ---------------------------------------------------------
# GEX & VEX VISUALIZATION
# ---------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Net GEX")
    html, near_gex, gex_strength = combined(gex, None, S)
    st.markdown(html, unsafe_allow_html=True)

with right:
    st.subheader("Net VEX")
    html2, near_vex, vex_strength = combined(vex, None, S, mode="vex")
    st.markdown(html2, unsafe_allow_html=True)


# ---------------------------------------------------------
# NEWS SECTION
# ---------------------------------------------------------
with st.expander("📰 Company News"):
    news_cards = fetch_company_news_cards(symbol, config.FINNHUB_TOKEN)
    if not news_cards:
        st.info("No recent headlines.")
    else:
        for c in news_cards:
            st.markdown(f"### [{c['headline']}]({c['url']})")
            st.caption(f"{c['source']} — {c['datetime']}")
            st.write(c.get('summary', ''))


# END OF FILE
