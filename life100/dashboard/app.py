"""Streamlit dashboard. SRS §30-32.

Thin by design — it only calls the FastAPI endpoints (ROADMAP §4.6: "the
dashboard MUST NOT become the simulation engine"). FastAPI is the graded
interface for this submission (SCOPE.md); this is the visual layer on top.
Charts use Altair (statistical charts) and pydeck (the World View's 3D
city render) — both ship as Streamlit dependencies already, no extra
services needed.

Visual language: a dark "command console" aesthetic (see design/*.png) —
near-black background, cyan/red/green/amber terminal accents, monospace
type throughout, bordered panels, a persistent top/bottom status bar, and
scrolling terminal-style log panels. A deliberate direction change from an
earlier "no glow/neon" pass — see SCOPE.md/PROGRESS.md.

Information architecture: a flat sidebar nav (matching the reference
screenshots), not nested tabs --

    CITY        -- what is happening?           (world map, metrics, event terminal)
    EXPERIMENT  -- what if we change one thing?  (What If?, Find the Breaking Point, Alternate Histories)
    INVESTIGATE -- why did it happen?            (causal graph + event inspector)
    PEOPLE      -- who is this happening to?     (citizen dossier, households, businesses)
    EVENTS      -- the raw historical record     (event log, type/volume breakdowns)
    DISASTERS   -- introduce a shock              (disaster triggers)
    AI AGENTS   -- governed AI, propose only      (Historian/Household/Government/Business)

A landing screen gates entry ("Enter the City" / "Run Guided Demo") so the
first thing a visitor sees is the city itself, not a control panel.
"""

from __future__ import annotations

import hashlib
import os

import altair as alt
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
HOURS_PER_DAY = 24  # matches life100.simulation.engine.HOURS_PER_DAY -- kept
# as a local constant rather than importing simulation code (the dashboard is
# a thin client, ROADMAP §4.6): simulation_tick on every event is hourly
# (SRS §9), used here only to format day/hour-of-day.

LF100_MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
# The console palette -- near-black ground, one cyan accent for
# primary/active state, red/green/amber for alert/positive/warning. Reused
# everywhere (charts, panels, terminal lines) instead of ad hoc hex codes.
BG = "#08090a"
BG_PANEL = "#0e1012"
BORDER = "#24272b"
TEXT = "#e4e6e8"
TEXT_MUTED = "#8a9096"
CYAN = "#2de0d6"
RED = "#ff5c5c"
GREEN = "#3ddc84"
AMBER = "#ffb84d"
VIOLET = "#9d8cf5"
BLUE = "#6fa8dc"

DISASTER_ENDPOINTS = {
    "Drought": "/disasters/drought",
    "Food shortage": "/disasters/food-shortage",
    "Flood": "/disasters/flood",
    "Earthquake": "/disasters/earthquake",
    "Disease outbreak": "/disasters/disease-outbreak",
    "Economic recession": "/disasters/economic-recession",
    "Energy crisis": "/disasters/energy-crisis",
}

NAV_ITEMS = [
    ("CITY", "◆"),
    ("EXPERIMENT", "▲"),
    ("INVESTIGATE", "◎"),
    ("PEOPLE", "●"),
    ("EVENTS", "▪"),
    ("DISASTERS", "⚠"),
    ("AI AGENTS", "◈"),
]


def _life100_altair_theme() -> dict:
    """One chart theme for the whole dashboard: near-black background, dark
    gridlines, monospace labels, and the console palette as the default
    categorical scale."""
    return {
        "config": {
            "background": "transparent",
            "view": {"stroke": "transparent"},
            "axis": {
                "domainColor": BORDER,
                "gridColor": "#17191c",
                "tickColor": BORDER,
                "labelColor": TEXT_MUTED,
                "titleColor": TEXT,
                "labelFont": LF100_MONO,
                "titleFont": LF100_MONO,
                "labelFontSize": 10,
                "titleFontSize": 11,
            },
            "legend": {
                "labelColor": TEXT_MUTED,
                "titleColor": TEXT,
                "labelFont": LF100_MONO,
                "labelFontSize": 10,
            },
            "title": {"color": TEXT, "fontSize": 12, "font": LF100_MONO},
            "range": {"category": [CYAN, RED, GREEN, AMBER, VIOLET, BLUE]},
        }
    }


alt.themes.register("life100_console", _life100_altair_theme)
alt.themes.enable("life100_console")


def api_get(path: str, **params) -> object:
    resp = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, payload: dict | None = None) -> requests.Response:
    return requests.post(f"{API_BASE_URL}{path}", json=payload or {}, timeout=60)


_CAUSE_LINK_KEYS = ("caused_by", "caused_by_disaster_event_id", "proposed_event_id")


def render_causal_chain(events_root_first: list[dict]) -> None:
    """Renders a real causal chain (root cause first, target event last) as
    a vertical box-and-arrow diagram -- "why did this happen?" made visible,
    not just a raw events table. Every box is an actual, recorded event; no
    inferred or invented step is ever drawn."""
    for i, e in enumerate(events_root_first):
        label = e["event_type"].replace("_", " ").upper()
        payload = e.get("payload") or {}
        detail = ", ".join(
            f"{k}={v}" for k, v in payload.items() if k not in _CAUSE_LINK_KEYS and not isinstance(v, (dict, list))
        )
        raw_tick = e.get("simulation_tick")
        day_label = raw_tick // HOURS_PER_DAY if isinstance(raw_tick, int) else "?"
        st.markdown(
            f'<div class="console-chain-box"><b>{label}</b>'
            f'<div class="console-chain-detail">DAY {day_label} · {detail[:140]}</div></div>',
            unsafe_allow_html=True,
        )
        if i < len(events_root_first) - 1:
            st.markdown('<div class="console-chain-arrow">▼</div>', unsafe_allow_html=True)


def render_terminal(lines: list[tuple[str, str, str]], title: str = "TERMINAL // EVENTS", height: int = 260) -> None:
    """A scrolling terminal-log panel: [tag] colored by level, timestamp,
    message. `lines` is (timestamp, level, message); level is one of
    ok/alert/warn/info and maps to green/red/amber/muted."""
    level_class = {"ok": "console-log-ok", "alert": "console-log-alert", "warn": "console-log-warn", "info": "console-log-info"}
    rows = "".join(
        f'<div class="console-log-row"><span class="console-log-ts">[{ts}]</span> '
        f'<span class="{level_class.get(level, "console-log-info")}">{msg}</span></div>'
        for ts, level, msg in lines
    )
    if not rows:
        rows = '<div class="console-log-row"><span class="console-log-ts">[--:--:--]</span> <span class="console-log-info">no events yet.</span></div>'
    st.markdown(
        f'<div class="console-panel-header">{title}</div>'
        f'<div class="console-terminal" style="height:{height}px">{rows}<div class="console-log-cursor">&gt; _</div></div>',
        unsafe_allow_html=True,
    )


def _event_log_lines(events: list[dict], limit: int = 12) -> list[tuple[str, str, str]]:
    """Turns raw event dicts into terminal-log lines with a real day/hour
    timestamp and a level derived from the event type (never fabricated)."""
    alert_types = {"JOB_LOST", "BUSINESS_FAILED", "DISASTER_STARTED", "HEALTH_IMPACTED", "CITIZEN_DIED", "DIVORCE"}
    ok_types = {"JOB_STARTED", "BUSINESS_EXPANDED", "MARRIAGE", "CHILD_BORN", "DISASTER_ENDED", "POLICY_CHANGED"}
    out = []
    for e in sorted(events, key=lambda x: -x["simulation_tick"])[:limit]:
        day, hour = divmod(e["simulation_tick"], HOURS_PER_DAY)
        ts = f"D{day:03d}.{hour:02d}:00"
        etype = e["event_type"]
        level = "alert" if etype in alert_types else "ok" if etype in ok_types else "info"
        label = etype.replace("_", " ")
        entity = e.get("source_entity", "")
        out.append((ts, level, f"{etype}: {label} — {entity}"))
    return out


st.set_page_config(page_title="LIFE/100", layout="wide", initial_sidebar_state="expanded")

# ============================================================================
# The console stylesheet -- every custom element in this file draws from
# this one system: near-black ground, monospace type, bordered panels, one
# cyan accent for active/primary state.
# ============================================================================
st.markdown(
    f"""
    <style>
    .stApp {{ background: {BG}; }}
    [data-testid="stHeader"] {{ background: transparent; }}
    [data-testid="stSidebar"] {{
        background: #000000; border-right: 1px solid {BORDER};
    }}
    [data-testid="stSidebar"] > div:first-child {{ padding-top: 1.2rem; }}
    body, .stApp, p, div, span {{ font-family: {LF100_MONO}; }}

    /* Streamlit stacks st.columns vertically below its own internal width
    breakpoint -- force every column row to stay side-by-side regardless of
    viewport width instead (a "console" layout is meant to read left/right,
    not collapse to one column on a narrower window). Columns shrink instead
    of stacking; content scrolls horizontally in its own panel if truly tight. */
    div[data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; align-items: flex-start; }}
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{ min-width: 0 !important; }}

    [data-testid="stMetricValue"] {{ font-family: {LF100_MONO}; font-variant-numeric: tabular-nums; color: {TEXT}; }}
    [data-testid="stMetricLabel"] {{ font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; color: {TEXT_MUTED}; }}

    .stButton button {{
        font-family: {LF100_MONO}; background: {BG_PANEL}; color: {TEXT};
        border: 1px solid {BORDER}; border-radius: 2px; letter-spacing: 0.03em;
    }}
    .stButton button:hover {{ border-color: {CYAN}; color: {CYAN}; }}
    .stButton button[kind="primary"] {{ background: {CYAN}; color: #001414; border-color: {CYAN}; font-weight: 700; }}
    .stButton button[kind="primary"]:hover {{ background: {TEXT}; border-color: {TEXT}; }}

    [data-testid="stSidebar"] .stRadio [role="radiogroup"] {{ gap: 1px; }}
    [data-testid="stSidebar"] .stRadio label {{
        font-family: {LF100_MONO}; padding: 9px 10px; border-radius: 2px;
        letter-spacing: 0.06em; font-size: 13px; color: {TEXT_MUTED}; width: 100%;
    }}
    [data-testid="stSidebar"] .stRadio label:has(input:checked) {{
        background: rgba(45, 224, 214, 0.09); border-left: 2px solid {CYAN}; color: {CYAN}; font-weight: 700;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{ color: {TEXT}; }}
    label[data-testid="stRadioOption"] > div:nth-child(2) > div:first-child > div:first-child {{ display: none !important; }}
    label[data-testid="stRadioOption"] {{ display: flex; }}
    label[data-testid="stRadioOption"]:has(input:checked) {{ color: {CYAN}; font-weight: 700; }}

    .console-brand {{ font-family: {LF100_MONO}; font-size: 30px; font-weight: 800; color: {TEXT}; letter-spacing: 0.02em; line-height: 1; }}
    .console-brand-sub {{ font-family: {LF100_MONO}; font-size: 10px; color: {TEXT_MUTED}; letter-spacing: 0.08em; margin: 4px 0 18px 0; }}

    .console-topbar {{
        font-family: {LF100_MONO}; display: flex; justify-content: space-between; align-items: center;
        border: 1px solid {BORDER}; border-radius: 2px; padding: 9px 16px; margin-bottom: 14px;
        background: {BG_PANEL}; font-size: 12px;
    }}
    .console-topbar-title {{ font-size: 20px; font-weight: 800; letter-spacing: 0.03em; color: {TEXT}; }}
    .console-dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: {CYAN}; margin-right: 6px; box-shadow: 0 0 6px {CYAN}; }}
    .console-topbar-right {{ color: {TEXT_MUTED}; letter-spacing: 0.05em; }}
    .console-topbar-right b {{ color: {TEXT}; }}

    .console-bottombar {{
        font-family: {LF100_MONO}; display: flex; justify-content: space-between; align-items: center;
        border-top: 1px solid {BORDER}; padding: 10px 4px; margin-top: 24px; font-size: 11px;
        color: {TEXT_MUTED}; letter-spacing: 0.04em;
    }}
    .console-bottombar .ok {{ color: {GREEN}; }}
    .console-bottombar span b {{ color: {TEXT}; }}

    .console-panel {{ border: 1px solid {BORDER}; border-radius: 2px; padding: 14px; background: {BG_PANEL}; margin-bottom: 14px; }}
    .console-panel-header {{
        font-family: {LF100_MONO}; font-size: 11px; letter-spacing: 0.08em; color: {TEXT_MUTED};
        text-transform: uppercase; border-bottom: 1px solid {BORDER}; padding-bottom: 8px; margin-bottom: 10px;
    }}
    .console-stat-row {{
        display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid #17191c; font-size: 12.5px;
    }}
    .console-stat-label {{ color: {TEXT_MUTED}; letter-spacing: 0.04em; text-transform: uppercase; font-size: 11px; }}
    .console-stat-value {{ color: {TEXT}; font-weight: 700; }}
    .console-stat-value.up {{ color: {GREEN}; }}
    .console-stat-value.down {{ color: {RED}; }}

    .console-terminal {{ overflow-y: auto; font-size: 11.5px; padding: 2px 0; }}
    .console-log-row {{ padding: 3px 0; border-bottom: 1px solid #131518; }}
    .console-log-ts {{ color: {TEXT_MUTED}; }}
    .console-log-ok {{ color: {GREEN}; }}
    .console-log-alert {{ color: {RED}; }}
    .console-log-warn {{ color: {AMBER}; }}
    .console-log-info {{ color: {TEXT}; }}
    .console-log-cursor {{ color: {CYAN}; margin-top: 4px; }}

    .console-chain-box {{ border: 1px solid {BORDER}; border-left: 2px solid {CYAN}; border-radius: 2px; padding: 9px 13px; margin: 2px 0; background: #0c0e10; }}
    .console-chain-box b {{ color: {TEXT}; font-size: 12.5px; letter-spacing: 0.02em; }}
    .console-chain-detail {{ font-family: {LF100_MONO}; font-size: 11px; color: {TEXT_MUTED}; margin-top: 3px; }}
    .console-chain-arrow {{ text-align: center; color: {TEXT_MUTED}; font-size: 14px; line-height: 1.6; }}

    .console-verdict {{ border: 1px solid {BORDER}; border-radius: 2px; padding: 11px 16px; margin: 6px 0 14px 0; font-size: 13.5px; font-weight: 700; }}
    .console-verdict-alert {{ border-left: 3px solid {RED}; color: {TEXT}; }}
    .console-verdict-calm {{ border-left: 3px solid {GREEN}; color: {TEXT_MUTED}; }}

    .console-landing-card {{ border: 1px solid {BORDER}; border-radius: 2px; padding: 32px 24px; margin: 18px 0; text-align: center; background: {BG_PANEL}; }}
    .console-landing-day {{ font-family: {LF100_MONO}; font-size: 30px; font-weight: 800; color: {CYAN}; letter-spacing: 0.04em; }}
    .console-landing-stats {{ font-family: {LF100_MONO}; font-size: 12.5px; color: {TEXT_MUTED}; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 10px; }}

    .console-evidence-bar {{ border: 1px solid {BORDER}; border-left: 3px solid {BLUE}; border-radius: 2px; padding: 8px 13px; margin: 6px 0; font-size: 12.5px; color: {TEXT}; }}
    .console-story-text {{ font-size: 16px; line-height: 1.6; margin: 18px 0; color: {TEXT}; }}
    .console-story-day {{ font-family: {LF100_MONO}; font-size: 22px; font-weight: 800; color: {CYAN}; }}
    .console-discovery {{ border: 1px solid {BORDER}; border-left: 3px solid {RED}; border-radius: 2px; padding: 20px 24px; margin: 16px 0; background: {BG_PANEL}; color: {TEXT}; }}

    .console-dossier-name {{ font-size: 26px; font-weight: 800; color: {TEXT}; letter-spacing: 0.01em; }}
    .console-dossier-label {{ font-size: 10px; color: {TEXT_MUTED}; letter-spacing: 0.1em; text-transform: uppercase; }}
    .console-badge {{ display: inline-block; border: 1px solid {BORDER}; border-radius: 2px; padding: 2px 8px; font-size: 10.5px; letter-spacing: 0.06em; color: {TEXT_MUTED}; margin-right: 6px; }}
    .console-badge.cyan {{ color: {CYAN}; border-color: {CYAN}; }}
    .console-badge.red {{ color: {RED}; border-color: {RED}; }}
    .console-badge.green {{ color: {GREEN}; border-color: {GREEN}; }}

    .console-bar-track {{ background: #17191c; border-radius: 2px; height: 6px; margin-top: 4px; overflow: hidden; }}
    .console-bar-fill {{ height: 100%; border-radius: 2px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.session_state.setdefault("entered_city", False)
st.session_state.setdefault("story_mode", False)
st.session_state.setdefault("story_step", 0)
st.session_state.setdefault("active_page", "CITY")


def render_top_bar(status: dict) -> None:
    """DAY N · SIMULATION ACTIVE -- the persistent header every reference
    screenshot shows, replacing the old horizontal metric strip."""
    st.markdown(
        f'<div class="console-topbar">'
        f'<span class="console-topbar-title">LIFE/100</span>'
        f'<span class="console-topbar-right"><b>DAY {status["day"]}</b>'
        f'&nbsp;&nbsp;<span class="console-dot"></span>SIMULATION ACTIVE</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_bottom_bar(status: dict) -> None:
    unemployment = status.get("unemployment_rate", 0.0) * 100
    st.markdown(
        f'<div class="console-bottombar">'
        f'<span class="ok">SYSTEM_STABLE_v1.0.2</span>'
        f'<span>POPULATION: <b>{status["population"]}</b> &nbsp;&nbsp; '
        f'FOOD_IDX: <b>{status["food_price_index"]:.2f}</b> &nbsp;&nbsp; '
        f'EMPLOYMENT: <b>{100 - unemployment:.1f}%</b> &nbsp;&nbsp; '
        f'BUSINESSES: <b>{status.get("active_businesses", "—")}</b></span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def stat_row(label: str, value: object, css_class: str = "") -> str:
    return (
        f'<div class="console-stat-row"><span class="console-stat-label">{label}</span>'
        f'<span class="console-stat-value {css_class}">{value}</span></div>'
    )


def bar(label: str, pct: float, color: str) -> str:
    pct = max(0.0, min(1.0, pct))
    return (
        f'<div style="margin:10px 0"><div class="console-stat-row" style="border:none;padding-bottom:2px">'
        f'<span class="console-stat-label">{label}</span><span class="console-stat-value">{pct * 100:.0f}%</span></div>'
        f'<div class="console-bar-track"><div class="console-bar-fill" style="width:{pct * 100:.0f}%;background:{color}"></div></div></div>'
    )


# ============================================================================
# Sidebar -- brand header, flat nav (matching design/*.png), Advanced Controls.
# ============================================================================
with st.sidebar:
    st.markdown('<div class="console-brand">LIFE/100</div>', unsafe_allow_html=True)
    st.markdown('<div class="console-brand-sub">LIFE/100<br>CIV_SIM_OS</div>', unsafe_allow_html=True)

    if st.session_state["entered_city"] and not st.session_state["story_mode"]:
        nav_labels = [f"{icon}  {label}" for label, icon in NAV_ITEMS]
        nav_map = {f"{icon}  {label}": label for label, icon in NAV_ITEMS}
        default_idx = [label for label, _ in NAV_ITEMS].index(st.session_state["active_page"])
        choice = st.radio("nav", nav_labels, index=default_idx, label_visibility="collapsed", key="nav_radio")
        st.session_state["active_page"] = nav_map[choice]
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    with st.expander("Advanced Controls", expanded=False):
        st.subheader("Found / restart the city")
        seed = st.number_input("Seed", value=847291, step=1, key="adv_seed")
        population = st.number_input("Population", value=100, min_value=5, max_value=500, step=5, key="adv_pop")
        if st.button("Start / Restart Simulation", type="primary", key="adv_start"):
            resp = api_post("/simulation/start", {"seed": int(seed), "population": int(population)})
            st.success(resp.json()) if resp.ok else st.error(resp.text)

        st.divider()
        st.subheader("Advance time (custom amount)")
        custom_ticks = st.number_input("Days", value=5, min_value=1, max_value=200, key="adv_ticks")
        if st.button("Advance", key="adv_tick_btn"):
            resp = api_post("/simulation/tick", {"ticks": 0, "days": int(custom_ticks)})
            st.write(resp.json() if resp.ok else resp.text)

    if st.session_state["entered_city"] and st.button("Return to landing screen"):
        st.session_state["entered_city"] = False
        st.session_state["story_mode"] = False
        st.session_state["story_step"] = 0
        st.rerun()

try:
    status = api_get("/simulation/status")
except requests.RequestException:
    status = None


# ============================================================================
# Landing screen
# ============================================================================
def render_landing(status: dict | None) -> None:
    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown('<div class="console-topbar-title" style="font-size:38px">LIFE/100</div>', unsafe_allow_html=True)
        st.caption("One city. A hundred lives. Infinite possible futures.")

        if status is None:
            st.markdown(
                '<div class="console-landing-card">'
                '<div class="console-landing-day">NO CITY YET</div>'
                '<div class="console-landing-stats">Found one to begin</div>'
                "</div>",
                unsafe_allow_html=True,
            )
            land_seed = st.number_input("Seed", value=847291, step=1, key="landing_seed")
            land_pop = st.number_input("Population", value=100, min_value=5, max_value=500, step=5, key="landing_pop")
            if st.button("Found the City", type="primary", use_container_width=True):
                resp = api_post("/simulation/start", {"seed": int(land_seed), "population": int(land_pop)})
                if resp.ok:
                    st.session_state["entered_city"] = True
                    st.rerun()
                else:
                    st.error(resp.text)
            return

        households_count = len(api_get("/households"))
        st.markdown(
            f'<div class="console-landing-card">'
            f'<div class="console-landing-day">DAY {status["day"]}</div>'
            f'<div class="console-landing-stats">{status["population"]} citizens &nbsp;·&nbsp; '
            f'{households_count} households &nbsp;·&nbsp; {status.get("active_businesses", "—")} businesses</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        enter_col, demo_col = st.columns(2)
        with enter_col:
            if st.button("Enter the City", type="primary", use_container_width=True):
                st.session_state["entered_city"] = True
                st.rerun()
        with demo_col:
            if st.button("Run Guided Demo", use_container_width=True):
                st.session_state["entered_city"] = True
                st.session_state["story_mode"] = True
                st.session_state["story_step"] = 0
                st.rerun()


if not st.session_state["entered_city"]:
    render_landing(status)
    st.stop()

if status is None:
    st.info("The city isn't reachable right now (API down?). Use Advanced Controls to found it once it's back.")
    st.stop()


# ============================================================================
# Story Mode -- a scripted PRESENTATION, not a scripted SIMULATION: every
# number shown is fetched live from a real API call made at that step.
# ============================================================================
def _advance_to_day(target_day: int) -> None:
    current = api_get("/simulation/status")["day"]
    if target_day > current:
        api_post("/simulation/tick", {"ticks": 0, "days": target_day - current})


def render_story_mode() -> None:
    step = st.session_state["story_step"]
    st.markdown('<div class="console-topbar-title">LIFE/100 — Guided Demo</div>', unsafe_allow_html=True)
    if st.button("Exit demo"):
        st.session_state["story_mode"] = False
        st.rerun()
    st.divider()

    if step == 0:
        s = api_get("/simulation/status")
        households_count = len(api_get("/households"))
        st.markdown(f'<div class="console-story-day">DAY {s["day"]}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="console-story-text">{s["population"]} citizens.<br>'
            f'{households_count} households.<br>'
            f'{s.get("active_businesses", "—")} businesses.<br><br>'
            f"Everything is stable.</div>",
            unsafe_allow_html=True,
        )
        if st.button("Begin", type="primary"):
            st.session_state["story_step"] = 1
            st.rerun()

    elif step == 1:
        if not st.session_state.get("story_drought_triggered"):
            api_post("/disasters/drought", {"duration_ticks": 40, "severity": 0.4})
            st.session_state["story_drought_triggered"] = True
        st.markdown('<div class="console-story-day">A drought has begun.</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="console-story-text">Food production is declining. Nothing else has been '
            "touched — everything from here on is the city's own economy reacting.</div>",
            unsafe_allow_html=True,
        )
        if st.button("Continue", type="primary"):
            st.session_state["story_step"] = 2
            st.rerun()

    elif step == 2:
        base_day = st.session_state.get("story_base_day", 0)
        _advance_to_day(base_day + 12)
        s = api_get("/simulation/status")
        st.markdown(f'<div class="console-story-day">DAY {s["day"]}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="console-story-text">Food prices have risen to '
            f'<b>{s["food_price_index"]:.2f}</b>× the baseline.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Continue", type="primary"):
            st.session_state["story_step"] = 3
            st.rerun()

    elif step == 3:
        base_day = st.session_state.get("story_base_day", 0)
        _advance_to_day(base_day + 18)
        s = api_get("/simulation/status")
        biz = api_get("/businesses")
        under_pressure = [b for b in biz if not b["active"] or b["cash"] < 0]
        st.markdown(f'<div class="console-story-day">DAY {s["day"]}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="console-story-text"><b>{len(under_pressure)}</b> businesses are under '
            f"financial pressure.</div>",
            unsafe_allow_html=True,
        )
        if st.button("Investigate", type="primary"):
            st.session_state["story_step"] = 4
            st.rerun()

    elif step == 4:
        events = api_get("/events", limit=2000)
        job_losses = [e for e in events if e["event_type"] == "JOB_LOST"]
        citizen_id = job_losses[-1]["source_entity"] if job_losses else None
        if citizen_id is None:
            st.markdown(
                '<div class="console-story-text">No one has lost their job yet — advance further and '
                "return to investigate a real story.</div>",
                unsafe_allow_html=True,
            )
        else:
            citizen = api_get(f"/citizens/{citizen_id}")
            st.markdown(f'<div class="console-story-day">{citizen["name"]}</div>', unsafe_allow_html=True)
            st.caption(f"{citizen['age']} years old · {citizen['occupation']}")
            st.markdown("**Why did their life change?**")
            resp = api_post(
                "/ai/historian/ask",
                {"citizen_id": citizen_id, "question": "Why did this citizen's employment situation change recently?"},
            )
            if resp.ok:
                answer = resp.json()
                st.markdown(f'<div class="console-story-text">{answer["answer"]}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="console-evidence-bar">Evidence grounded — '
                    f'{len(answer["cited_event_ids"])} cited event(s) of '
                    f'{answer["evidence_considered"]} considered. No fabricated citation is possible: '
                    f"the Historian is rejected if it ever cites an event it wasn't shown.</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("(Historian unavailable right now — continuing anyway.)")
        if st.button("What if we intervene?", type="primary"):
            st.session_state["story_step"] = 5
            st.rerun()

    elif step == 5:
        st.markdown('<div class="console-story-day">What if we intervene?</div>', unsafe_allow_html=True)
        if "story_experiment" not in st.session_state:
            resp = api_post(
                "/experiments/run",
                {
                    "ticks": 20,
                    "scenarios": [
                        {"name": "World A — No Intervention", "disaster": "drought", "disaster_duration": 30, "disaster_severity": 0.4},
                        {"name": "World B — Food Subsidy", "disaster": "drought", "disaster_duration": 30, "disaster_severity": 0.4,
                         "policies": {"food_subsidy": 0.5}},
                        {"name": "World C — Emergency Employment", "disaster": "drought", "disaster_duration": 30,
                         "disaster_severity": 0.4, "emergency_employment": True},
                    ],
                },
            )
            if resp.ok:
                st.session_state["story_experiment"] = resp.json()
            else:
                st.error(f"Experiment failed: {resp.text}")
        experiment = st.session_state.get("story_experiment")
        if experiment:
            control = experiment["control"]["metrics"]
            cols = st.columns(4)
            cols[0].markdown("**Control**")
            cols[0].metric("Unemployment", f"{control['unemployment_rate'] * 100:.1f}%")
            for col, s in zip(cols[1:], experiment["scenarios"]):
                col.markdown(f"**{s['name'].split('—')[-1].strip()}**")
                col.metric(
                    "Unemployment",
                    f"{s['metrics']['unemployment_rate'] * 100:.1f}%",
                    delta=f"{(s['metrics']['unemployment_rate'] - control['unemployment_rate']) * 100:+.1f}pp",
                    delta_color="inverse",
                )
        if st.button("Where does the city break?", type="primary"):
            st.session_state["story_step"] = 6
            st.rerun()

    elif step == 6:
        st.markdown('<div class="console-story-day">Where does the city break?</div>', unsafe_allow_html=True)
        if "story_sensitivity" not in st.session_state:
            resp = api_post(
                "/experiments/sensitivity",
                {"parameter": "drought_severity", "values": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5], "ticks": 15},
            )
            if resp.ok:
                st.session_state["story_sensitivity"] = resp.json()
            else:
                st.error(f"Sensitivity sweep failed: {resp.text}")
        sensitivity = st.session_state.get("story_sensitivity")
        if sensitivity:
            sens_df = pd.DataFrame(sensitivity["metrics_by_value"])
            sens_df.insert(0, "severity", sensitivity["values"])
            tp = sensitivity["tipping_points"].get("business_failures")
            line = (
                alt.Chart(sens_df)
                .mark_line(point=True, color=CYAN)
                .encode(x=alt.X("severity:Q", title="Drought severity"), y=alt.Y("business_failures:Q"))
                .properties(height=240, title="business_failures")
            )
            if tp:
                lo, hi = tp["bracket"]
                band = (
                    alt.Chart(pd.DataFrame({"lo": [lo], "hi": [hi]}))
                    .mark_rect(opacity=0.2, color=RED)
                    .encode(x="lo:Q", x2="hi:Q")
                )
                st.altair_chart(band + line, use_container_width=True)
            else:
                st.altair_chart(line, use_container_width=True)
        if st.button("See the discovery", type="primary"):
            st.session_state["story_step"] = 7
            st.rerun()

    elif step == 7:
        sensitivity = st.session_state.get("story_sensitivity")
        tp = sensitivity["tipping_points"].get("business_failures") if sensitivity else None
        st.markdown('<div class="console-story-day">The city has a breaking point.</div>', unsafe_allow_html=True)
        if tp:
            refined = tp.get("refined_bracket") or tp["bracket"]
            st.markdown(
                f'<div class="console-discovery">'
                f"Drought severity <b>{refined[0]:.3f}–{refined[1]:.3f}</b> is where business failures "
                f"begin — a jump {tp['ratio']:.1f}× the typical step size.<br><br>"
                f"The transition was not scripted. It emerged from the interaction of the city's "
                f"existing economic rules: a business fails only once its cumulative cash crosses "
                f"zero — a hard threshold sitting on top of a smooth, linear relationship between "
                f"drought severity and cost pressure.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="console-discovery">No tipping point was found in this range — the response '
                "was smooth. That negative result is itself part of the evidence: this system reports "
                "what it actually finds, not what would make a better story.</div>",
                unsafe_allow_html=True,
            )
        if st.button("Exit demo", type="primary"):
            st.session_state["story_mode"] = False
            for key in ("story_step", "story_drought_triggered", "story_experiment", "story_sensitivity", "story_base_day"):
                st.session_state.pop(key, None)
            st.rerun()


if st.session_state["story_mode"]:
    st.session_state.setdefault("story_base_day", status["day"])
    render_story_mode()
    st.stop()

# Fetched once, shared across every page below.
households_df = pd.DataFrame(api_get("/households"))
households_df["members"] = households_df["member_ids"].apply(len)
businesses_df = pd.DataFrame(api_get("/businesses"))
citizens_df = pd.DataFrame(api_get("/citizens"))
employer_ids = sorted(businesses_df["business_id"].tolist()) if len(businesses_df) else []
name_by_id = {c["citizen_id"]: c["name"] for c in citizens_df.to_dict(orient="records")}

render_top_bar(status)

# ============================================================================
# CITY -- the sector view: world map, global metrics, live event terminal.
# ============================================================================
def render_city() -> None:
    main_col, side_col = st.columns([2.1, 1])

    with main_col:
        st.markdown('<div class="console-panel-header">SEC-01 // SECTOR VIEW</div>', unsafe_allow_html=True)
        ZONE_COLORS = {
            "residential": [30, 60, 45, 210],
            "commercial": [24, 52, 78, 210],
            "industrial": [70, 52, 32, 210],
            "park": [20, 58, 30, 235],
            "road": [16, 18, 20, 255],
        }
        BUILDING_STYLE = {
            "home": {"color": [45, 224, 214], "height": 16, "half_size": 0.26},
            "shop": {"color": [111, 168, 220], "height": 26, "half_size": 0.32},
            "factory": {"color": [255, 184, 77], "height": 40, "half_size": 0.40},
            "school": {"color": [157, 140, 245], "height": 32, "half_size": 0.36},
            "hospital": {"color": [255, 92, 92], "height": 36, "half_size": 0.36},
            "bank": {"color": [255, 210, 100], "height": 38, "half_size": 0.34},
            "government": {"color": [228, 230, 232], "height": 50, "half_size": 0.42},
        }
        STRESS_LOW_COLOR = [61, 220, 132]
        STRESS_HIGH_COLOR = [255, 92, 92]
        GRID_SCALE = 0.0012
        BUILDING_MATERIAL = {"ambient": 0.3, "diffuse": 0.6, "shininess": 40, "specularColor": [45, 224, 214]}

        def _stable_jitter(key: str, spread: float) -> float:
            digest = int(hashlib.md5(key.encode()).hexdigest(), 16)
            return ((digest % 2001) / 1000.0 - 1.0) * spread

        def _lerp_color(low: list[int], high: list[int], t: float) -> list[int]:
            t = max(0.0, min(1.0, t))
            return [round(low[i] + (high[i] - low[i]) * t) for i in range(3)]

        def _footprint(x: float, y: float, half_size: float) -> list[list[float]]:
            corners = ((-half_size, -half_size), (half_size, -half_size), (half_size, half_size), (-half_size, half_size))
            return [[(x + dx) * GRID_SCALE, (y + dy) * GRID_SCALE] for dx, dy in corners]

        world = api_get("/world")
        width, height_dim = world["width"], world["height"]
        stress_by_building = {
            h["home_building_id"]: h["financial_stress"] for h in households_df.to_dict(orient="records") if h.get("home_building_id")
        }
        business_by_building = {b["building_id"]: b for b in businesses_df.to_dict(orient="records")}
        household_by_building = {
            h["home_building_id"]: h for h in households_df.to_dict(orient="records") if h.get("home_building_id")
        }

        zone_data = []
        for z in world["zones"]:
            base = ZONE_COLORS.get(z["kind"], [60, 60, 64, 200])
            jitter = _stable_jitter(f"zone_{z['x']}_{z['y']}", 6)
            color = [max(0, min(255, c + jitter)) for c in base[:3]] + [base[3]]
            elevation = 3 if z["kind"] == "park" else 0
            zone_data.append({"polygon": _footprint(z["x"] + 0.5, z["y"] + 0.5, 0.5), "color": color, "elevation": elevation})

        road_cells = {(z["x"], z["y"]) for z in world["zones"] if z["kind"] == "road"}
        road_segments = []
        for x, y in road_cells:
            cx, cy = (x + 0.5) * GRID_SCALE, (y + 0.5) * GRID_SCALE
            for nx, ny in ((x + 1, y), (x, y + 1)):
                if (nx, ny) in road_cells:
                    road_segments.append({"source": [cx, cy], "target": [(nx + 0.5) * GRID_SCALE, (ny + 0.5) * GRID_SCALE]})

        building_data = []
        for b in world["buildings"]:
            style = BUILDING_STYLE.get(b["kind"], {"color": [200, 200, 200], "height": 20, "half_size": 0.3})
            if b["kind"] == "home" and b["building_id"] in stress_by_building:
                color = _lerp_color(STRESS_LOW_COLOR, STRESS_HIGH_COLOR, stress_by_building[b["building_id"]])
            else:
                jitter = _stable_jitter(b["building_id"] + "c", 10)
                color = [max(0, min(255, c + jitter)) for c in style["color"]]
            height_jitter = _stable_jitter(b["building_id"] + "h", style["height"] * 0.18)
            building_data.append(
                {
                    "polygon": _footprint(b["x"] + 0.5, b["y"] + 0.5, style["half_size"]),
                    "color": color,
                    "elevation": max(6, style["height"] + height_jitter),
                    "kind": b["kind"],
                    "building_id": b["building_id"],
                    "stress": (
                        round(stress_by_building[b["building_id"]], 3)
                        if b["building_id"] in stress_by_building
                        else ("vacant" if b["kind"] == "home" else "n/a")
                    ),
                }
            )

        ground_layer = pdk.Layer(
            "PolygonLayer", zone_data, get_polygon="polygon", get_fill_color="color", get_elevation="elevation",
            extruded=True, stroked=False, filled=True, pickable=False,
        )
        road_layer = pdk.Layer(
            "LineLayer", road_segments, get_source_position="source", get_target_position="target",
            get_color=[45, 224, 214, 90], get_width=2, width_min_pixels=1,
        )
        building_layer = pdk.Layer(
            "PolygonLayer", building_data, id="buildings", get_polygon="polygon", get_fill_color="color",
            get_elevation="elevation", extruded=True, wireframe=True, get_line_color=[45, 224, 214, 140],
            material=BUILDING_MATERIAL, pickable=True, auto_highlight=True, highlight_color=[45, 224, 214, 120],
        )
        view_state = pdk.ViewState(
            longitude=(width / 2) * GRID_SCALE, latitude=(height_dim / 2) * GRID_SCALE, zoom=14.85, pitch=55, bearing=28,
        )
        deck = pdk.Deck(
            layers=[ground_layer, road_layer, building_layer], initial_view_state=view_state, map_provider=None,
            tooltip={"text": "{kind}\n{building_id}\nhousehold stress: {stress}"},
        )
        map_event = st.pydeck_chart(deck, height=460, on_select="rerun", selection_mode="single-object", key="world_map")
        st.caption(
            f"{world['city_id']} — seed {world['seed']} — {width}x{height_dim} grid — "
            "drag to orbit, scroll to zoom, click a building to inspect — homes tinted by real financial stress"
        )

        selected_objects = []
        if map_event is not None:
            selection = getattr(map_event, "selection", None) or {}
            selected_objects = (selection.get("objects") or {}).get("buildings") or []

        if selected_objects:
            obj = selected_objects[0]
            building_id = obj.get("building_id")
            kind = obj.get("kind")
            st.markdown(f"#### {building_id}")
            if kind == "home":
                hh = household_by_building.get(building_id)
                if hh:
                    pcol1, pcol2, pcol3 = st.columns(3)
                    pcol1.metric("Financial stress", f"{hh['financial_stress']:.2f}")
                    pcol2.metric("Savings", hh["savings"])
                    pcol3.metric("Members", hh["members"])
                else:
                    st.caption("Vacant home.")
            else:
                biz = business_by_building.get(building_id)
                if biz:
                    at_risk = (not biz["active"]) or biz["cash"] < 0
                    st.caption(biz["industry"].replace("_", " ").title())
                    pcol1, pcol2, pcol3 = st.columns(3)
                    pcol1.metric("Cash", biz["cash"])
                    pcol2.metric("Employees", biz["headcount"])
                    pcol3.metric("Status", "AT RISK" if at_risk else "STABLE")
                    if at_risk and st.button("Why?", key=f"why_{building_id}"):
                        recent = api_get("/events", limit=5000)
                        biz_events = [e for e in recent if (e.get("payload") or {}).get("business_id") == building_id]
                        biz_id_matches = [e for e in recent if e.get("source_entity") == biz.get("business_id")]
                        biz_events = biz_events + [e for e in biz_id_matches if e not in biz_events]
                        failures = [e for e in biz_events if e["event_type"] == "BUSINESS_FAILED"]
                        layoffs = [e for e in biz_events if e["event_type"] == "JOB_LOST"]
                        anchor = failures[-1] if failures else (layoffs[-1] if layoffs else None)
                        if anchor is None:
                            st.caption("No recorded events reference this business yet.")
                        else:
                            causes = api_get(f"/events/{anchor['event_id']}/causes")
                            render_causal_chain(list(reversed(causes)))
                else:
                    st.caption("No business record for this building.")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="console-panel-header">ADVANCE TIME</div>', unsafe_allow_html=True)
        step_cols = st.columns(4)
        with step_cols[0]:
            day_clicked = st.button("+1 Day", use_container_width=True)
        with step_cols[1]:
            five_clicked = st.button("+5 Days", use_container_width=True)
        with step_cols[2]:
            thirty_clicked = st.button("+30 Days", use_container_width=True)
        with step_cols[3]:
            ov_disaster = st.selectbox("disaster", list(DISASTER_ENDPOINTS), key="ov_disaster", label_visibility="collapsed")
            introduce_clicked = st.button(f"Introduce {ov_disaster}", use_container_width=True)

        advance_amount = 1 if day_clicked else 5 if five_clicked else 30 if thirty_clicked else 0
        if advance_amount:
            tick_before = status["tick"]
            resp = api_post("/simulation/tick", {"ticks": 0, "days": advance_amount})
            if resp.ok:
                recent = api_get("/events", limit=500)
                new_events = [e for e in recent if e["simulation_tick"] > tick_before]
                st.session_state["recent_feed"] = sorted(new_events, key=lambda e: (-e["simulation_tick"], e["event_id"]))[:30]
            else:
                st.error(resp.text)
            st.rerun()
        if introduce_clicked:
            resp = api_post(DISASTER_ENDPOINTS[ov_disaster], {})
            st.success(f"{ov_disaster} introduced.") if resp.ok else st.error(resp.text)
            st.rerun()

        with st.expander("Economy trends"):
            econ_col1, econ_col2 = st.columns(2)
            series = pd.DataFrame(api_get("/simulation/metrics-timeseries"))
            if len(series) > 1:
                with econ_col1:
                    st.altair_chart(
                        alt.Chart(series).mark_line(color=RED, point=True).encode(
                            x=alt.X("day:Q", title="Day"), y=alt.Y("food_price_index:Q", title="Food price index"),
                        ).properties(height=180, title="FOOD PRICE INDEX"),
                        use_container_width=True,
                    )
                with econ_col2:
                    employment_df = series.melt(id_vars=["day"], value_vars=["employed", "active_businesses"], var_name="metric", value_name="value")
                    st.altair_chart(
                        alt.Chart(employment_df).mark_line(point=True).encode(
                            x=alt.X("day:Q", title="Day"), y=alt.Y("value:Q", title="Count"),
                            color=alt.Color("metric:N", title=None, scale=alt.Scale(range=[GREEN, AMBER])),
                        ).properties(height=180, title="EMPLOYMENT & BUSINESSES"),
                        use_container_width=True,
                    )

    with side_col:
        st.markdown('<div class="console-panel">', unsafe_allow_html=True)
        st.markdown('<div class="console-panel-header">SYS_METRICS // GLOBAL</div>', unsafe_allow_html=True)
        working_age_unemployment = status.get("unemployment_rate", 0.0) * 100
        rows_html = "".join(
            [
                stat_row("POPULATION", status["population"]),
                stat_row("HOUSEHOLDS", len(households_df)),
                stat_row("EMPLOYMENT", f"{100 - working_age_unemployment:.1f}%", "up" if working_age_unemployment < 20 else "down"),
                stat_row("AVG_WEALTH", f"${citizens_df['savings'].mean():,.0f}" if "savings" in citizens_df.columns and len(citizens_df) else "—"),
                stat_row("FOOD_IDX", f"{status['food_price_index']:.2f}", "down" if status["food_price_index"] > 1.5 else ""),
                stat_row("BUSINESSES", status.get("active_businesses", "—")),
                stat_row("HEALTH INCIDENTS", status.get("health_incidents", 0)),
            ]
        )
        st.markdown(rows_html, unsafe_allow_html=True)
        disasters = status.get("active_disasters_detail") or {}
        if disasters:
            parts = []
            for name, info in disasters.items():
                mag = info.get("magnitude")
                mag_txt = f" (sev {mag:.2f})" if isinstance(mag, (int, float)) and mag else ""
                parts.append(f"{name.replace('_', ' ').upper()}{mag_txt}")
            st.markdown(
                f'<div style="margin-top:8px;color:{RED};font-size:11.5px;letter-spacing:0.04em">'
                f'⚠ {" · ".join(parts)} ACTIVE</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        events = api_get("/events", limit=200)
        render_terminal(_event_log_lines(events, limit=14), title="TERMINAL // EVENTS", height=420)


# ============================================================================
# EXPERIMENT -- What If? / Find the Breaking Point / Alternate Histories,
# stacked as sections on one page (flat nav, no nested tabs).
# ============================================================================
def render_experiment() -> None:
    section = st.radio(
        "experiment section", ["WHAT IF?", "FIND THE BREAKING POINT", "ALTERNATE HISTORIES"],
        horizontal=True, label_visibility="collapsed", key="experiment_section",
    )
    if section == "WHAT IF?":
        _render_what_if()
    elif section == "FIND THE BREAKING POINT":
        _render_breaking_point()
    else:
        _render_alternate_histories()


def _render_what_if() -> None:
    st.markdown('<div class="console-panel-header">INJECTION PARAMETERS // WHAT IF?</div>', unsafe_allow_html=True)
    st.caption(
        "Branches the CURRENT simulation into a Control plus intervention worlds, runs every one for "
        "the same number of days, and reports real measured outcomes — there is no lookup table."
    )
    experiment = st.session_state.get("last_experiment")
    with st.expander("Configure experiment", expanded=not experiment):
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            st.markdown("**Scenario**")
            exp_disaster = st.selectbox(
                "Disaster",
                ["drought", "food_shortage", "flood", "earthquake", "disease_outbreak", "economic_recession", "energy_crisis"],
                key="exp_disaster",
            )
            exp_duration = st.slider("Duration (days)", 5, 90, 30, key="exp_duration")
            exp_severity = st.slider("Drought severity (only applies to drought)", 0.1, 1.0, 0.4, step=0.05, key="exp_severity")
            exp_ticks = st.slider("Days to run", 5, 90, 30, key="exp_ticks")
        with exp_col2:
            st.markdown("**Government intervention (World B)**")
            exp_food_subsidy = st.slider("Food subsidy", 0.0, 1.0, 0.5, step=0.05, key="exp_food_subsidy")
            exp_interest_rate = st.slider("Interest rate", 0.0, 0.3, 0.05, step=0.01, key="exp_interest_rate")
            exp_healthcare = st.slider("Healthcare funding", 0.0, 1.0, 0.5, step=0.05, key="exp_healthcare")
            st.markdown("**World C**")
            st.caption("Emergency employment program (a demand stimulus, not scripted mass-hiring)")

        if st.button("▲  INTRODUCE DISASTER (run 3 futures)", type="primary"):
            exp_request = {
                "ticks": int(exp_ticks),
                "scenarios": [
                    {"name": "World A — No Intervention", "disaster": exp_disaster, "disaster_duration": int(exp_duration),
                     "disaster_severity": float(exp_severity)},
                    {"name": "World B — Food Subsidy", "disaster": exp_disaster, "disaster_duration": int(exp_duration),
                     "disaster_severity": float(exp_severity),
                     "policies": {"food_subsidy": float(exp_food_subsidy), "interest_rate": float(exp_interest_rate),
                                  "healthcare_spending": float(exp_healthcare)}},
                    {"name": "World C — Emergency Employment", "disaster": exp_disaster, "disaster_duration": int(exp_duration),
                     "disaster_severity": float(exp_severity), "emergency_employment": True},
                ],
            }
            resp = api_post("/experiments/run", exp_request)
            if resp.ok:
                st.session_state["experiment_counter"] = st.session_state.get("experiment_counter", 0) + 1
                st.session_state["last_experiment"] = resp.json()
                st.rerun()
            else:
                st.error(resp.text)

    experiment = st.session_state.get("last_experiment")
    if experiment:
        traj_col, impact_col = st.columns([1.3, 1])
        control_metrics = experiment["control"]["metrics"]
        worlds = [{"name": "Control (Baseline)", "metrics": control_metrics}] + [
            {"name": s["name"], "metrics": s["metrics"]} for s in experiment["scenarios"]
        ]
        with traj_col:
            st.markdown('<div class="console-panel-header">DIVERGENCE TRAJECTORY — UNEMPLOYMENT_RATE</div>', unsafe_allow_html=True)
            # Best-effort trajectory: shared starting point -> each world's real
            # final measured value (the full per-tick series per branch isn't
            # returned by /experiments/run — this still shows real divergence
            # from one shared point, not per-hour interpolation).
            traj_rows = []
            for w in worlds:
                traj_rows.append({"world": w["name"], "t": "start", "unemployment_rate": control_metrics["unemployment_rate"]})
                traj_rows.append({"world": w["name"], "t": "end", "unemployment_rate": w["metrics"]["unemployment_rate"]})
            traj_df = pd.DataFrame(traj_rows)
            st.altair_chart(
                alt.Chart(traj_df).mark_line(point=True, strokeWidth=2).encode(
                    x=alt.X("t:N", title=None, sort=["start", "end"]), y=alt.Y("unemployment_rate:Q", title="Unemployment rate"),
                    color=alt.Color("world:N", title=None),
                ).properties(height=260),
                use_container_width=True,
            )
        with impact_col:
            st.markdown('<div class="console-panel-header">IMPACT PROJECTIONS</div>', unsafe_allow_html=True)
            rows_html = ""
            for w in worlds[1:]:
                m = w["metrics"]
                delta_unemp = (m["unemployment_rate"] - control_metrics["unemployment_rate"]) * 100
                cls = "down" if delta_unemp > 0 else "up"
                rows_html += f'<div style="margin-bottom:10px"><b style="color:{TEXT};font-size:12px">{w["name"]}</b>'
                rows_html += stat_row("UNEMPLOYMENT", f"{m['unemployment_rate']*100:.1f}% ({delta_unemp:+.1f}pp)", cls)
                rows_html += stat_row("BUSINESS_FAILURES", f"{m['business_failures']} ({m['business_failures']-control_metrics['business_failures']:+d})",
                                       "down" if m["business_failures"] > control_metrics["business_failures"] else "up")
                rows_html += stat_row("HEALTH_INCIDENTS", m["health_incidents"])
                rows_html += "</div>"
            st.markdown(f'<div class="console-panel">{rows_html}</div>', unsafe_allow_html=True)

        with st.expander("Full metrics table"):
            result_df = pd.DataFrame([{"world": w["name"], **w["metrics"]} for w in worlds])
            st.dataframe(
                result_df[["world", "food_price_index", "unemployment_rate", "employment", "business_failures",
                            "health_incidents", "avg_household_wealth", "avg_household_stress"]],
                use_container_width=True,
            )

        world_options = {experiment["control"]["simulation_id"]: "Control"} | {
            s["simulation_id"]: s["name"] for s in experiment["scenarios"]
        }
        chosen_world = st.selectbox("Activate a world (then use INVESTIGATE on its events)", list(world_options), format_func=lambda sid: world_options[sid], key="exp_inspect")
        if st.button("Activate this world"):
            resp = api_post(f"/simulation/activate/{chosen_world}")
            st.write(resp.json() if resp.ok else resp.text)
    else:
        st.caption("Run 3 futures to see the divergence trajectory and impact projections here.")


def _render_breaking_point() -> None:
    st.markdown('<div class="console-panel-header">FIND THE BREAKING POINT</div>', unsafe_allow_html=True)
    st.caption(
        "Sweeps drought severity, branching an independent world at each value, looking for a "
        "disproportionate jump — never forced. A smooth metric is reported as having no tipping point."
    )
    sensitivity = st.session_state.get("last_sensitivity")
    with st.expander("Configure sweep", expanded=not sensitivity):
        sens_col1, sens_col2, sens_col3 = st.columns(3)
        with sens_col1:
            sens_min = st.slider("Minimum severity", 0.05, 0.45, 0.05, step=0.05, key="sens_min")
        with sens_col2:
            sens_max = st.slider("Maximum severity", 0.1, 1.0, 0.5, step=0.05, key="sens_max")
        with sens_col3:
            sens_steps = st.slider("Number of steps", 4, 16, 10, key="sens_steps")
        sens_ticks = st.slider("Days to run each branch", 3, 30, 15, key="sens_ticks")

        if st.button("Run Sensitivity Sweep", type="primary"):
            if sens_max <= sens_min:
                st.error("Maximum severity must be greater than minimum severity.")
            else:
                step_size = (sens_max - sens_min) / (sens_steps - 1)
                sweep_values = [round(sens_min + i * step_size, 4) for i in range(sens_steps)]
                resp = api_post("/experiments/sensitivity", {"parameter": "drought_severity", "values": sweep_values, "ticks": int(sens_ticks)})
                if resp.ok:
                    st.session_state["last_sensitivity"] = resp.json()
                    st.rerun()
                else:
                    st.error(resp.text)

    sensitivity = st.session_state.get("last_sensitivity")
    if sensitivity:
        found = [m for m, tp in sensitivity["tipping_points"].items() if tp]
        if found:
            st.markdown(
                f'<div class="console-verdict console-verdict-alert">Tipping point found in '
                f"{', '.join(found)} — {len(found)} of {len(sensitivity['tipping_points'])} swept metrics show a genuine break.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="console-verdict console-verdict-calm">No tipping point found anywhere in this range.</div>', unsafe_allow_html=True)

        sens_df = pd.DataFrame(sensitivity["metrics_by_value"])
        sens_df.insert(0, "severity", sensitivity["values"])
        sens_metrics = ["business_failures", "unemployment_rate", "health_incidents", "avg_household_wealth"]
        sens_chart_cols = st.columns(2)
        for idx, metric in enumerate(sens_metrics):
            tp = sensitivity["tipping_points"].get(metric)
            line = alt.Chart(sens_df).mark_line(point=True, color=CYAN).encode(
                x=alt.X("severity:Q", title="Drought severity"), y=alt.Y(f"{metric}:Q"),
            ).properties(height=190, title=metric)
            with sens_chart_cols[idx % 2]:
                if tp:
                    lo, hi = tp["bracket"]
                    band = alt.Chart(pd.DataFrame({"lo": [lo], "hi": [hi]})).mark_rect(opacity=0.2, color=RED).encode(x="lo:Q", x2="hi:Q")
                    st.altair_chart(band + line, use_container_width=True)
                    refined = tp.get("refined_bracket")
                    located = f"{refined[0]:.3f}–{refined[1]:.3f}" if refined else f"{lo:.2f}–{hi:.2f}"
                    st.caption(f"Tipping point: severity {located} (jump {tp['ratio']:.1f}× typical step)")
                else:
                    st.altair_chart(line, use_container_width=True)
                    st.caption("No tipping point — smooth response.")
    else:
        st.caption("Run a sweep to see the severity-response curve.")


def _render_alternate_histories() -> None:
    st.markdown('<div class="console-panel-header">ALTERNATE HISTORIES</div>', unsafe_allow_html=True)
    new_id = st.text_input("New simulation_id", value=f"{status['simulation_id']}_branch")
    if st.button("Branch"):
        resp = api_post("/simulation/branch", {"new_simulation_id": new_id})
        st.write(resp.json() if resp.ok else resp.text)

    sims = api_get("/simulation/list")
    sim_rows = sims["simulations"]
    if sim_rows:
        timeline_bars, fork_points = [], []
        for row in sim_rows:
            branch_info = row.get("branch_info")
            start_day = branch_info["branch_point_day"] if branch_info else 0
            timeline_bars.append({"simulation_id": row["simulation_id"], "start": start_day, "end": row["day"]})
            if branch_info:
                fork_points.append({"simulation_id": row["simulation_id"], "day": branch_info["branch_point_day"]})
        bars_df = pd.DataFrame(timeline_bars)
        bar_chart = alt.Chart(bars_df).mark_bar(height=14, color=BLUE).encode(
            x=alt.X("start:Q", title="Day"), x2="end:Q", y=alt.Y("simulation_id:N", title=None),
        ).properties(height=32 * len(bars_df) + 20)
        if fork_points:
            fork_df = pd.DataFrame(fork_points)
            fork_marks = alt.Chart(fork_df).mark_tick(color=RED, thickness=2, size=20).encode(x="day:Q", y=alt.Y("simulation_id:N", title=None))
            st.altair_chart(bar_chart + fork_marks, use_container_width=True)
        else:
            st.altair_chart(bar_chart, use_container_width=True)
    st.dataframe(pd.DataFrame(sim_rows), use_container_width=True)
    st.caption(f"Active: {sims['active_simulation_id']}")

    sim_ids = [s["simulation_id"] for s in sim_rows]
    if len(sim_ids) >= 2:
        a = st.selectbox("Timeline A", sim_ids, index=0)
        b = st.selectbox("Timeline B", sim_ids, index=min(1, len(sim_ids) - 1))
        if st.button("Compare"):
            comparison = api_get("/simulation/compare", simulation_a=a, simulation_b=b)
            div_col1, div_col2 = st.columns(2)
            with div_col1:
                st.caption(a)
                st.dataframe(pd.DataFrame(comparison["divergent_events"][a]), use_container_width=True, height=200)
            with div_col2:
                st.caption(b)
                st.dataframe(pd.DataFrame(comparison["divergent_events"][b]), use_container_width=True, height=200)
    if sim_ids:
        activate_id = st.selectbox("Activate", sim_ids, key="activate_select")
        if st.button("Set active"):
            resp = api_post(f"/simulation/activate/{activate_id}")
            st.write(resp.json() if resp.ok else resp.text)


# ============================================================================
# INVESTIGATE -- causal graph + event detail inspector + sys log.
# ============================================================================
def render_investigate() -> None:
    graph_col, inspect_col = st.columns([1.4, 1])
    events_df = pd.DataFrame(api_get("/events", limit=500))

    with graph_col:
        st.markdown('<div class="console-panel-header">CAUSAL GRAPH // TRACE</div>', unsafe_allow_html=True)
        st.caption("Every arrow is an explicit, recorded `caused_by` link — never inferred or fabricated.")
        event_id = st.text_input("event_id", value=events_df["event_id"].iloc[-1] if len(events_df) else "")
        traced = None
        if st.button("Run Counterfactual Trace", type="primary") and event_id:
            causes = api_get(f"/events/{event_id}/causes")
            effects = api_get(f"/events/{event_id}/effects")
            st.session_state["trace_result"] = {"event_id": event_id, "causes": causes, "effects": effects}
        traced = st.session_state.get("trace_result")
        if traced and traced["event_id"] == event_id:
            st.markdown("**Causal chain (root cause → this event)**")
            if traced["causes"]:
                render_causal_chain(list(reversed(traced["causes"])))
            else:
                st.caption("event not found.")

    with inspect_col:
        st.markdown('<div class="console-panel-header">EVENT DETAIL INSPECTOR</div>', unsafe_allow_html=True)
        if traced:
            effects = traced["effects"]
            affected = {e["source_entity"] for e in effects}
            st.markdown(f'<div class="console-panel">', unsafe_allow_html=True)
            st.markdown(f'<span class="console-badge cyan">ID: {traced["event_id"]}</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"**DOWNSTREAM (PREDICTED EFFECTS)**", unsafe_allow_html=True)
            st.markdown(
                f'<div style="color:{RED};font-size:12.5px">{len(effects)} event(s) directly caused by this one, '
                f'touching {len(affected)} entit(y/ies).</div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
            if effects:
                st.dataframe(pd.DataFrame(effects)[["event_type", "simulation_tick", "source_entity"]], use_container_width=True)
            else:
                st.caption("Nothing has cited this event as its cause (yet) — a leaf in the causal graph so far.")
            with st.expander("Raw causes/effects tables"):
                st.dataframe(pd.DataFrame(traced["causes"]), use_container_width=True)
                st.dataframe(pd.DataFrame(traced["effects"]), use_container_width=True)
        else:
            st.caption("Trace an event_id to inspect it here.")

    st.divider()
    if len(events_df):
        events_df["simulation_day"] = events_df["simulation_tick"] // HOURS_PER_DAY
        recent_events = events_df.to_dict(orient="records")
    else:
        recent_events = []
    render_terminal(_event_log_lines(recent_events, limit=14), title="SYS_LOG // CAUSAL ENGINE", height=220)


# ============================================================================
# PEOPLE -- citizen dossier + households + businesses.
# ============================================================================
def render_people() -> None:
    people_scope = st.radio("scope", ["CITIZENS", "HOUSEHOLDS", "BUSINESSES"], horizontal=True, label_visibility="collapsed", key="people_scope")

    if people_scope == "CITIZENS":
        list_col, dossier_col = st.columns([1, 1.6])
        with list_col:
            query = st.text_input("QUERY_CITIZEN_ID", key="citizen_query", label_visibility="collapsed", placeholder="query_citizen_id ...")
            rows = citizens_df.copy()
            if query:
                rows = rows[rows["citizen_id"].str.contains(query, case=False) | rows["name"].str.contains(query, case=False)]
            rows = rows.sort_values("age", ascending=False)
            st.markdown('<div class="console-panel-header">PEOPLE DIRECTORY</div>', unsafe_allow_html=True)
            options = rows["citizen_id"].tolist()
            if options:
                selected_citizen = st.radio(
                    "citizen", options,
                    format_func=lambda cid: f"{name_by_id.get(cid, cid)}  ({cid})",
                    label_visibility="collapsed", key="citizen_pick",
                )
            else:
                selected_citizen = None
                st.caption("No citizens match.")

        with dossier_col:
            if selected_citizen:
                c = api_get(f"/citizens/{selected_citizen}")
                st.markdown('<div class="console-dossier-label">DOSSIER // PRIMARY TARGET</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="console-dossier-name">{c["name"]}</div>', unsafe_allow_html=True)
                status_badge = "cyan" if c.get("alive", True) else "red"
                st.markdown(
                    f'<span class="console-badge {status_badge}">{"ALIVE" if c.get("alive", True) else "DECEASED"}</span>'
                    f'<span class="console-badge">CITIZEN_ID: {c["citizen_id"]}</span>'
                    f'<span class="console-badge">AGE: {c["age"]}</span>'
                    f'<span class="console-badge">{c.get("occupation", "—").upper()}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

                vit_col, psych_col = st.columns(2)
                with vit_col:
                    rows_html = "".join([
                        stat_row("GENDER", c.get("gender", "—")),
                        stat_row("EDUCATION", c.get("education_level", "—")),
                        stat_row("MARITAL_STATUS", c.get("marital_status", "—")),
                        stat_row("HEALTH_SCORE", f"{c.get('health_score', 0):.2f}", "up" if c.get("health_score", 0) > 0.6 else "down"),
                        stat_row("CREDIT_SCORE", c.get("credit_score", "—")),
                    ])
                    st.markdown(f'<div class="console-panel"><div class="console-panel-header">VITALS_SYS</div>{rows_html}</div>', unsafe_allow_html=True)
                with psych_col:
                    personality = c.get("personality") or {}
                    bars_html = (
                        bar("STRESS_LEVEL", c.get("stress", 0), RED)
                        + bar("RISK_TOLERANCE", personality.get("risk_tolerance", 0), CYAN)
                        + bar("AMBITION", personality.get("ambition", 0), GREEN)
                        + bar("SOCIAL_TENDENCY", personality.get("social_tendency", 0), VIOLET)
                    )
                    st.markdown(f'<div class="console-panel"><div class="console-panel-header">PSYCH_PROFILE</div>{bars_html}</div>', unsafe_allow_html=True)

                econ_col, chrono_col = st.columns(2)
                with econ_col:
                    rows_html = "".join([
                        stat_row("LIQUID_CAPITAL", f"{c.get('savings', 0):,.2f}"),
                        stat_row("DEBT", f"{c.get('debt', 0):,.2f}"),
                        stat_row("SALARY", f"{c.get('salary', 0):,.2f}"),
                        stat_row("EMPLOYER", c.get("employer_id") or "NONE"),
                    ])
                    st.markdown(f'<div class="console-panel"><div class="console-panel-header">ECONOMIC_STATUS & ASSETS</div>{rows_html}</div>', unsafe_allow_html=True)
                with chrono_col:
                    timeline = api_get(f"/citizens/{selected_citizen}/timeline")
                    lines = _event_log_lines(timeline, limit=8)
                    render_terminal(lines, title="CHRONOLOGY // EVENTS", height=180)

                if st.button("▶  INITIATE INTERVENTION", type="primary", key="init_intervention"):
                    resp = api_post("/ai/household/propose", {"citizen_id": selected_citizen, "decision_context": "AI-initiated intervention review"})
                    st.write(resp.json() if resp.ok else resp.text)

                st.divider()
                if st.button("Explain my story", key="explain_story_btn"):
                    resp = api_post(
                        "/ai/historian/ask",
                        {"citizen_id": selected_citizen, "question": "Tell this citizen's story so far — what has happened to them and why?"},
                    )
                    if resp.ok:
                        answer = resp.json()
                        st.markdown(answer["answer"])
                        st.markdown(
                            f'<div class="console-evidence-bar">Evidence grounded — {len(answer["cited_event_ids"])} cited '
                            f'event(s) of {answer["evidence_considered"]} considered.</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error(resp.text)
            else:
                st.caption("Select a citizen from the directory.")

        with st.expander("Population statistics"):
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            with stat_col1:
                st.altair_chart(
                    alt.Chart(citizens_df).mark_bar(color=CYAN).encode(
                        x=alt.X("age:Q", bin=alt.Bin(maxbins=20), title="Age"), y=alt.Y("count():Q", title="Citizens"),
                    ).properties(height=190, title="AGE DISTRIBUTION"), use_container_width=True,
                )
            with stat_col2:
                occ_counts = citizens_df["occupation"].value_counts().reset_index()
                occ_counts.columns = ["occupation", "count"]
                st.altair_chart(
                    alt.Chart(occ_counts).mark_bar(color=AMBER).encode(
                        x=alt.X("count:Q", title="Citizens"), y=alt.Y("occupation:N", sort="-x", title=None),
                    ).properties(height=190, title="OCCUPATION BREAKDOWN"), use_container_width=True,
                )
            with stat_col3:
                citizens_df["net_worth"] = citizens_df["savings"] - citizens_df["debt"]
                st.altair_chart(
                    alt.Chart(citizens_df).mark_bar(color=GREEN).encode(
                        x=alt.X("net_worth:Q", bin=alt.Bin(maxbins=20), title="Net worth"), y=alt.Y("count():Q", title="Citizens"),
                    ).properties(height=190, title="WEALTH DISTRIBUTION"), use_container_width=True,
                )

    elif people_scope == "HOUSEHOLDS":
        st.markdown('<div class="console-panel-header">HOUSEHOLD REGISTRY</div>', unsafe_allow_html=True)
        st.dataframe(
            households_df[["household_id", "members", "home_building_id", "property_value", "income", "expenses",
                            "savings", "debt", "financial_stress", "living_conditions"]],
            use_container_width=True, height=250,
        )
        hh_col1, hh_col2 = st.columns(2)
        with hh_col1:
            st.altair_chart(
                alt.Chart(households_df).mark_circle(size=90, color=AMBER, opacity=0.8).encode(
                    x=alt.X("savings:Q", title="Household savings"), y=alt.Y("financial_stress:Q", title="Financial stress"),
                    size=alt.Size("members:Q", title="Members"),
                ).properties(height=260, title="SAVINGS VS STRESS"), use_container_width=True,
            )
        with hh_col2:
            st.altair_chart(
                alt.Chart(households_df).mark_bar(color=VIOLET).encode(
                    x=alt.X("financial_stress:Q", bin=alt.Bin(maxbins=15), title="Financial stress"), y=alt.Y("count():Q", title="Households"),
                ).properties(height=260, title="STRESS DISTRIBUTION"), use_container_width=True,
            )

    else:
        st.markdown('<div class="console-panel-header">BUSINESS REGISTRY</div>', unsafe_allow_html=True)
        st.dataframe(businesses_df, use_container_width=True, height=250)
        if len(businesses_df):
            biz_col1, biz_col2 = st.columns(2)
            with biz_col1:
                industry_counts = businesses_df["industry"].value_counts().reset_index()
                industry_counts.columns = ["industry", "count"]
                st.altair_chart(
                    alt.Chart(industry_counts).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta("count:Q"), color=alt.Color("industry:N", title="Industry"),
                    ).properties(height=260, title="BY INDUSTRY"), use_container_width=True,
                )
            with biz_col2:
                top_businesses = businesses_df.sort_values("cash", ascending=False)
                st.altair_chart(
                    alt.Chart(top_businesses).mark_bar().encode(
                        x=alt.X("cash:Q", title="Cash"), y=alt.Y("business_id:N", sort="-x", title=None),
                        color=alt.Color("active:N", title="Active", scale=alt.Scale(range=[RED, GREEN])),
                    ).properties(height=260, title="CASH ON HAND"), use_container_width=True,
                )


# ============================================================================
# EVENTS -- the raw historical record.
# ============================================================================
def render_events() -> None:
    st.markdown('<div class="console-panel-header">EVENT LOG // HISTORICAL RECORD</div>', unsafe_allow_html=True)
    events_df = pd.DataFrame(api_get("/events", limit=500))
    if len(events_df):
        ev_col1, ev_col2 = st.columns(2)
        with ev_col1:
            type_counts = events_df["event_type"].value_counts().reset_index()
            type_counts.columns = ["event_type", "count"]
            st.altair_chart(
                alt.Chart(type_counts).mark_bar(color=VIOLET).encode(
                    x=alt.X("count:Q", title="Count"), y=alt.Y("event_type:N", sort="-x", title=None),
                ).properties(height=300, title="EVENT TYPE BREAKDOWN (LAST 500)"), use_container_width=True,
            )
        with ev_col2:
            events_df["simulation_day"] = events_df["simulation_tick"] // HOURS_PER_DAY
            by_day = events_df.groupby("simulation_day", as_index=False).size()
            st.altair_chart(
                alt.Chart(by_day).mark_bar(color=CYAN).encode(
                    x=alt.X("simulation_day:Q", title="Day"), y=alt.Y("size:Q", title="Events"),
                ).properties(height=300, title="EVENT VOLUME PER DAY (LAST 500)"), use_container_width=True,
            )
        st.markdown('<div class="console-panel-header">RAW EVENT LOG</div>', unsafe_allow_html=True)
        st.dataframe(events_df, use_container_width=True, height=320)
    else:
        st.caption("No events yet — advance time from CITY.")


# ============================================================================
# DISASTERS -- introduce a shock.
# ============================================================================
def render_disasters() -> None:
    param_col, log_col = st.columns([1.3, 1])
    with param_col:
        st.markdown('<div class="console-panel-header">DISASTER TRIGGERS</div>', unsafe_allow_html=True)
        disaster_label = st.selectbox("Disaster", list(DISASTER_ENDPOINTS), key="dis_disaster")
        disaster_payload: dict = {}
        if disaster_label == "Drought":
            disaster_payload["severity"] = st.slider("Severity", 0.1, 1.0, 0.4, step=0.05, key="dis_drought_severity")
        elif disaster_label in ("Flood", "Earthquake"):
            disaster_payload["damage_fraction"] = st.slider(
                "Damage fraction", 0.1, 1.0, 0.7, step=0.05, key="dis_damage_fraction",
                help="Fraction of each affected business's cash wiped out. A business fails outright "
                     "if what's left can't cover its own operating expenses.",
            )
            disaster_payload["affected_share"] = st.slider("Share of businesses affected", 0.05, 1.0, 0.3, step=0.05, key="dis_affected_share")
        if st.button(f"⚠  INTRODUCE {disaster_label.upper()}", type="primary", key="dis_trigger_btn"):
            resp = api_post(DISASTER_ENDPOINTS[disaster_label], disaster_payload)
            if resp.ok:
                st.success(f"{disaster_label} introduced.")
            else:
                st.error(resp.text)

        st.divider()
        st.markdown('<div class="console-panel-header">ACTIVE DISASTERS</div>', unsafe_allow_html=True)
        active = api_get("/disasters/active")["active_disasters"]
        if active:
            rows_html = ""
            for name, info in active.items():
                mag = info.get("magnitude")
                mag_txt = f"{mag:.2f}" if isinstance(mag, (int, float)) else "—"
                rows_html += stat_row(name.replace("_", " ").upper(), f"severity {mag_txt}", "down")
            st.markdown(f'<div class="console-panel">{rows_html}</div>', unsafe_allow_html=True)
        else:
            st.caption("No active disasters.")

    with log_col:
        events = [e for e in api_get("/events", limit=300) if e["event_type"] in ("DISASTER_STARTED", "DISASTER_ENDED", "BUSINESS_CONTRACTED", "HEALTH_IMPACTED")]
        render_terminal(_event_log_lines(events, limit=14), title="SYSTEM_LOG", height=420)


# ============================================================================
# AI AGENTS -- governed AI. Every proposal: propose -> validate -> accept/reject -> apply.
# ============================================================================
def render_ai_agents() -> None:
    st.markdown('<div class="console-panel-header">AI AGENTS // DECISION ROOM</div>', unsafe_allow_html=True)
    st.caption(
        "These agents don't touch the city directly. Every proposal below passes through the same "
        "pipeline: propose → validate against hard bounds → accept or reject → apply — each step its "
        "own event in the log (see INVESTIGATE). An agent that suggests something out of bounds gets "
        "rejected, not silently clamped."
    )

    hist_col, gov_col = st.columns(2)
    with hist_col:
        st.markdown('<div class="console-panel"><div class="console-panel-header">HISTORIAN AGENT</div>', unsafe_allow_html=True)
        st.caption("Grounded in real events, never fabricated citations")
        h_citizen = st.selectbox("Citizen", list(name_by_id), format_func=lambda cid: name_by_id[cid], key="hist_citizen")
        question = st.text_input("Question", value="Why did this citizen's situation change?")
        if st.button("Ask Historian"):
            resp = api_post("/ai/historian/ask", {"citizen_id": h_citizen, "question": question})
            st.write(resp.json() if resp.ok else resp.text)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="console-panel"><div class="console-panel-header">HOUSEHOLD DECISION AGENT</div>', unsafe_allow_html=True)
        st.caption("Proposes, never decides unilaterally")
        decision_context = st.text_input("Decision context", value="considering a major loan")
        if st.button("Ask Household Agent"):
            resp = api_post("/ai/household/propose", {"citizen_id": h_citizen, "decision_context": decision_context})
            st.write(resp.json() if resp.ok else resp.text)
        st.markdown("</div>", unsafe_allow_html=True)

    with gov_col:
        st.markdown('<div class="console-panel"><div class="console-panel-header">GOVERNMENT AGENT</div>', unsafe_allow_html=True)
        st.caption(f"Sees: food price {status['food_price_index']:.2f}, active disasters {', '.join(status['active_disasters']) or 'none'}")
        if st.button("Propose Policy"):
            resp = api_post("/ai/government/propose")
            st.write(resp.json() if resp.ok else resp.text)
            st.caption("validator checks it against ALLOWED_POLICY_ACTIONS bounds before anything applies")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="console-panel"><div class="console-panel-header">BUSINESS AGENT</div>', unsafe_allow_html=True)
        st.caption("Proposes hire/fire/loan actions, bounded by validator.py")
        if employer_ids:
            b_id = st.selectbox("Business", employer_ids)
            if st.button("Propose Business Action"):
                resp = api_post(f"/ai/business/{b_id}/propose")
                st.write(resp.json() if resp.ok else resp.text)
        else:
            st.caption("No businesses with current employees to select yet.")
        st.markdown("</div>", unsafe_allow_html=True)


PAGE_RENDERERS = {
    "CITY": render_city,
    "EXPERIMENT": render_experiment,
    "INVESTIGATE": render_investigate,
    "PEOPLE": render_people,
    "EVENTS": render_events,
    "DISASTERS": render_disasters,
    "AI AGENTS": render_ai_agents,
}

PAGE_RENDERERS[st.session_state["active_page"]]()

render_bottom_bar(status)
