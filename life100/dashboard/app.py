"""Streamlit dashboard. SRS §30-32.

Thin by design — it only calls the FastAPI endpoints (ROADMAP §4.6: "the
dashboard MUST NOT become the simulation engine"). FastAPI is the graded
interface for this submission (SCOPE.md); this is the visual layer on top.
"""

from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def api_get(path: str, **params) -> object:
    resp = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, payload: dict | None = None) -> requests.Response:
    return requests.post(f"{API_BASE_URL}{path}", json=payload or {}, timeout=60)


st.set_page_config(page_title="LIFE/100", layout="wide")
st.title("LIFE/100")
st.caption("Only 100 people. Every life matters.")

DISASTER_ENDPOINTS = {
    "Drought": "/disasters/drought",
    "Food shortage": "/disasters/food-shortage",
    "Flood": "/disasters/flood",
    "Earthquake": "/disasters/earthquake",
    "Disease outbreak": "/disasters/disease-outbreak",
    "Economic recession": "/disasters/economic-recession",
    "Energy crisis": "/disasters/energy-crisis",
}

with st.sidebar:
    st.header("Simulation Control")
    seed = st.number_input("Seed", value=847291, step=1)
    population = st.number_input("Population", value=100, min_value=5, max_value=500, step=5)
    if st.button("▶ Start / Restart Simulation", type="primary"):
        resp = api_post("/simulation/start", {"seed": int(seed), "population": int(population)})
        st.success(resp.json()) if resp.ok else st.error(resp.text)

    st.divider()
    ticks = st.number_input("Ticks to advance", value=5, min_value=1, max_value=200)
    if st.button("⏩ Advance Simulation"):
        resp = api_post("/simulation/tick", {"ticks": int(ticks)})
        st.write(resp.json() if resp.ok else resp.text)

    st.divider()
    st.subheader("Trigger a Disaster")
    disaster_label = st.selectbox("Disaster", list(DISASTER_ENDPOINTS))
    if st.button(f"⚠ Trigger {disaster_label}"):
        resp = api_post(DISASTER_ENDPOINTS[disaster_label], {})
        st.write(resp.json() if resp.ok else resp.text)

try:
    status = api_get("/simulation/status")
except requests.RequestException:
    status = None

if status is None:
    st.info("Start a simulation from the sidebar to begin (or the API isn't reachable yet).")
    st.stop()

tabs = st.tabs(
    ["World View", "City Dashboard", "Citizens", "Households", "Businesses", "Events & Causality", "AI Agents", "Alternate Timelines"]
)

# -- World View (SRS §30.1) ------------------------------------------------
ZONE_COLORS = {
    "residential": "#d9f2d9",
    "commercial": "#cfe3ff",
    "industrial": "#f5d6b3",
    "park": "#a6d9a6",
    "road": "#d8d8d8",
}
BUILDING_ICONS = {
    "home": "🏠",
    "school": "🏫",
    "hospital": "🏥",
    "shop": "🏪",
    "factory": "🏭",
    "bank": "🏦",
    "government": "🏛",
}

with tabs[0]:
    world = api_get("/world")
    zone_kind = {(z["x"], z["y"]): z["kind"] for z in world["zones"]}
    building_icon = {(b["x"], b["y"]): BUILDING_ICONS.get(b["kind"], "?") for b in world["buildings"]}

    rows_html = []
    for y in range(world["height"]):
        cells = []
        for x in range(world["width"]):
            color = ZONE_COLORS.get(zone_kind.get((x, y), "road"), "#eee")
            icon = building_icon.get((x, y), "")
            cells.append(
                f'<td style="background:{color};width:28px;height:28px;text-align:center;'
                f'font-size:14px;border:1px solid #ffffff33;">{icon}</td>'
            )
        rows_html.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        f'<table style="border-collapse:collapse">{"".join(rows_html)}</table>',
        unsafe_allow_html=True,
    )
    legend = " &nbsp; ".join(f'<span style="background:{c};padding:2px 6px">{k}</span>' for k, c in ZONE_COLORS.items())
    st.markdown(legend, unsafe_allow_html=True)
    st.caption(f"{world['city_id']} — seed {world['seed']} — {world['width']}x{world['height']} grid")

# -- City Dashboard (SRS §30.5) ------------------------------------------
with tabs[1]:
    cols = st.columns(5)
    cols[0].metric("Tick", status["tick"])
    cols[1].metric("Food price index", status["food_price_index"])
    cols[2].metric("Population", status["population"])
    cols[3].metric("Active disasters", ", ".join(status["active_disasters"]) or "none")
    cols[4].metric("Events logged", status["events_logged"])

    citizens = api_get("/citizens")
    citizens_df = pd.DataFrame(citizens)
    working_age = citizens_df[(citizens_df["age"] >= 18) & (citizens_df["age"] <= 65)]
    unemployment_rate = (
        round((working_age["occupation"] == "unemployed").mean() * 100, 1) if len(working_age) else 0.0
    )
    avg_wealth = round((citizens_df["savings"] - citizens_df["debt"]).mean(), 2) if len(citizens_df) else 0.0

    cols2 = st.columns(4)
    cols2[0].metric("Unemployment rate", f"{unemployment_rate}%")
    cols2[1].metric("Average wealth", avg_wealth)
    cols2[2].metric("Policies active", len(status["policies"]) or "none")
    cols2[3].metric("Simulation ID", status["simulation_id"])

    st.json(status["policies"] or {"food_subsidy": 0, "tax_rate": 0.15, "interest_rate": 0.05})

# -- Citizens (SRS §30.2) -------------------------------------------------
with tabs[2]:
    citizens_df = pd.DataFrame(api_get("/citizens"))
    st.dataframe(
        citizens_df[["citizen_id", "name", "age", "occupation", "employer_id", "salary", "savings", "stress"]],
        use_container_width=True,
        height=250,
    )
    name_by_id = {c["citizen_id"]: c["name"] for c in citizens_df.to_dict(orient="records")}
    selected_citizen = st.selectbox(
        "Inspect a citizen", list(name_by_id), format_func=lambda cid: f"{name_by_id[cid]} ({cid})"
    )
    detail_col, memory_col = st.columns(2)
    with detail_col:
        st.json(api_get(f"/citizens/{selected_citizen}"))
    with memory_col:
        st.markdown("**Significant memories** (SRS §25)")
        st.dataframe(pd.DataFrame(api_get(f"/citizens/{selected_citizen}/memories")), use_container_width=True)
        st.markdown("**Relationships** (SRS §12)")
        st.dataframe(pd.DataFrame(api_get(f"/citizens/{selected_citizen}/relationships")), use_container_width=True)
    st.markdown(f"**Timeline — {name_by_id.get(selected_citizen, selected_citizen)}**")
    st.dataframe(pd.DataFrame(api_get(f"/citizens/{selected_citizen}/timeline")), use_container_width=True, height=200)

# -- Households (SRS §30.3) ----------------------------------------------
with tabs[3]:
    households = {c["household_id"] for c in citizens_df.to_dict(orient="records") if c.get("household_id")}
    rows = []
    for hh_id in sorted(households):
        members = citizens_df[citizens_df["household_id"] == hh_id]
        rows.append(
            {
                "household_id": hh_id,
                "members": len(members),
                "total_income": members["salary"].sum(),
                "total_savings": members["savings"].sum(),
                "total_debt": members["debt"].sum(),
                "avg_stress": round(members["stress"].mean(), 3),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=300)

# -- Businesses (SRS §30.4) -----------------------------------------------
with tabs[4]:
    businesses_df = pd.DataFrame(api_get("/businesses"))
    st.dataframe(businesses_df, use_container_width=True, height=300)
    employer_ids = sorted(businesses_df["business_id"].tolist()) if len(businesses_df) else []

# -- Events & Causality (SRS §30.6, §22-23) -------------------------------
with tabs[5]:
    events_df = pd.DataFrame(api_get("/events", limit=200))
    st.dataframe(events_df, use_container_width=True, height=300)

    st.markdown("**Trace a causal chain**")
    event_id = st.text_input("event_id", value=events_df["event_id"].iloc[-1] if len(events_df) else "")
    causes_col, effects_col = st.columns(2)
    if st.button("Trace") and event_id:
        with causes_col:
            st.markdown("Causes (backward)")
            st.dataframe(pd.DataFrame(api_get(f"/events/{event_id}/causes")), use_container_width=True)
        with effects_col:
            st.markdown("Effects (forward — butterfly effect)")
            st.dataframe(pd.DataFrame(api_get(f"/events/{event_id}/effects")), use_container_width=True)

# -- AI Agents (SRS §30.7) -------------------------------------------------
with tabs[6]:
    hist_col, gov_col = st.columns(2)
    with hist_col:
        st.markdown("**Historian Agent**")
        h_citizen = st.selectbox(
            "Citizen", list(name_by_id), format_func=lambda cid: name_by_id[cid], key="hist_citizen"
        )
        question = st.text_input("Question", value="Why did this citizen's situation change?")
        if st.button("🕵 Ask Historian"):
            resp = api_post("/ai/historian/ask", {"citizen_id": h_citizen, "question": question})
            st.write(resp.json() if resp.ok else resp.text)

        st.markdown("**Household Decision Agent**")
        decision_context = st.text_input("Decision context", value="considering a major loan")
        if st.button("🏠 Ask Household Agent"):
            resp = api_post(
                "/ai/household/propose", {"citizen_id": h_citizen, "decision_context": decision_context}
            )
            st.write(resp.json() if resp.ok else resp.text)

    with gov_col:
        st.markdown("**Government Agent**")
        if st.button("🏛 Propose Policy"):
            resp = api_post("/ai/government/propose")
            st.write(resp.json() if resp.ok else resp.text)

        st.markdown("**Business Agent**")
        if employer_ids:
            b_id = st.selectbox("Business", employer_ids)
            if st.button("🏢 Propose Business Action"):
                resp = api_post(f"/ai/business/{b_id}/propose")
                st.write(resp.json() if resp.ok else resp.text)
        else:
            st.caption("No businesses with current employees to select yet.")

# -- Alternate Timelines (SRS §27-29) -------------------------------------
with tabs[7]:
    st.markdown("**Branch the current simulation**")
    new_id = st.text_input("New simulation_id", value=f"{status['simulation_id']}_branch")
    if st.button("🌿 Branch"):
        resp = api_post("/simulation/branch", {"new_simulation_id": new_id})
        st.write(resp.json() if resp.ok else resp.text)

    sims = api_get("/simulation/list")
    st.dataframe(pd.DataFrame(sims["simulations"]), use_container_width=True)
    st.caption(f"Active: {sims['active_simulation_id']}")

    sim_ids = [s["simulation_id"] for s in sims["simulations"]]
    if len(sim_ids) >= 2:
        st.markdown("**Compare two timelines**")
        a = st.selectbox("Timeline A", sim_ids, index=0)
        b = st.selectbox("Timeline B", sim_ids, index=min(1, len(sim_ids) - 1))
        if st.button("⚖ Compare"):
            comparison = api_get("/simulation/compare", simulation_a=a, simulation_b=b)
            st.json(comparison)
    else:
        st.caption("Branch at least once to compare timelines.")

    st.markdown("**Activate a simulation** (existing tick/disaster/AI actions act on whichever is active)")
    if sim_ids:
        activate_id = st.selectbox("Activate", sim_ids, key="activate_select")
        if st.button("Set active"):
            resp = api_post(f"/simulation/activate/{activate_id}")
            st.write(resp.json() if resp.ok else resp.text)
