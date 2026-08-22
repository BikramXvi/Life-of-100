"""Thin Streamlit dashboard. It is NOT the source of truth — it only calls
the FastAPI endpoints (ROADMAP §4.6: "the dashboard MUST NOT become the
simulation engine"). FastAPI is the graded interface for this submission;
this is a visual layer on top of it (see SCOPE.md)."""

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
    duration = st.number_input("Drought duration (ticks)", value=20, min_value=1, max_value=200)
    if st.button("🌵 Trigger Drought"):
        resp = api_post("/disasters/drought", {"duration_ticks": int(duration)})
        st.write(resp.json() if resp.ok else resp.text)

try:
    status = api_get("/simulation/status")
except requests.RequestException:
    status = None

if status is None:
    st.info("Start a simulation from the sidebar to begin (or the API isn't reachable yet).")
else:
    cols = st.columns(5)
    cols[0].metric("Tick", status["tick"])
    cols[1].metric("Food price index", status["food_price_index"])
    cols[2].metric("Population", status["population"])
    cols[3].metric("Active disasters", ", ".join(status["active_disasters"]) or "none")
    cols[4].metric("Events logged", status["events_logged"])

    citizens = api_get("/citizens")
    citizens_df = pd.DataFrame(citizens)

    st.subheader("Citizens")
    st.dataframe(
        citizens_df[["citizen_id", "name", "age", "occupation", "employer_id", "salary", "savings", "stress"]],
        use_container_width=True,
        height=250,
    )

    st.subheader("Ask an AI Agent")
    ai_col1, ai_col2 = st.columns(2)

    with ai_col1:
        st.markdown("**Historian Agent** — evidence-grounded explanation")
        name_by_id = {c["citizen_id"]: c["name"] for c in citizens}
        selected = st.selectbox(
            "Citizen", list(name_by_id), format_func=lambda cid: f"{name_by_id[cid]} ({cid})"
        )
        question = st.text_input("Question", value="Why did this citizen's situation change?")
        if st.button("🕵 Ask Historian"):
            resp = api_post("/ai/historian/ask", {"citizen_id": selected, "question": question})
            if resp.ok:
                data = resp.json()
                st.write(data["answer"])
                st.caption(f"Cited events: {data['cited_event_ids']}")
            else:
                st.error(resp.text)

        st.markdown(f"**Timeline — {name_by_id.get(selected, selected)}**")
        timeline = api_get(f"/citizens/{selected}/timeline")
        st.dataframe(pd.DataFrame(timeline), use_container_width=True, height=200)

    with ai_col2:
        st.markdown("**Government Agent** — propose → validate → apply")
        if st.button("🏛 Propose Policy"):
            resp = api_post("/ai/government/propose")
            st.write(resp.json() if resp.ok else resp.text)

        st.markdown("**Recent Events (all citizens)**")
        events = api_get("/events", limit=100)
        st.dataframe(pd.DataFrame(events), use_container_width=True, height=250)
