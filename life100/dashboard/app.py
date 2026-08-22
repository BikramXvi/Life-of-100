"""Streamlit dashboard. SRS §30-32.

Thin by design — it only calls the FastAPI endpoints (ROADMAP §4.6: "the
dashboard MUST NOT become the simulation engine"). FastAPI is the graded
interface for this submission (SCOPE.md); this is the visual layer on top.
Charts use Altair (statistical charts) and pydeck (the World View's 3D
city render) — both ship as Streamlit dependencies already, no extra
services needed.
"""

from __future__ import annotations

import os

import altair as alt
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# A shared dark theme so every chart matches the dashboard's own look
# rather than Vega-Lite's default light background.
alt.themes.enable("dark")


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

# ============================================================================
# World View (SRS §30.1) — a real rendered 3D city, not a flat table.
# ============================================================================
ZONE_COLORS = {
    "residential": [96, 176, 96, 140],
    "commercial": [80, 130, 220, 140],
    "industrial": [230, 150, 60, 140],
    "park": [56, 138, 56, 170],
    "road": [70, 70, 76, 120],
}
BUILDING_STYLE = {
    "home": {"color": [255, 205, 120], "height": 16},
    "shop": {"color": [110, 175, 255], "height": 28},
    "factory": {"color": [255, 130, 80], "height": 42},
    "school": {"color": [175, 130, 255], "height": 34},
    "hospital": {"color": [255, 90, 90], "height": 38},
    "bank": {"color": [255, 215, 90], "height": 40},
    "government": {"color": [235, 235, 235], "height": 52},
}
GRID_SCALE = 0.0012  # degrees per grid cell (~130m) -- purely a rendering trick, not real geography

with tabs[0]:
    world = api_get("/world")
    width, height_dim = world["width"], world["height"]

    zone_data = [
        {
            "polygon": [
                [(z["x"] + dx) * GRID_SCALE, (z["y"] + dy) * GRID_SCALE]
                for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1))
            ],
            "color": ZONE_COLORS.get(z["kind"], [90, 90, 90, 100]),
        }
        for z in world["zones"]
    ]
    building_data = [
        {
            "position": [(b["x"] + 0.5) * GRID_SCALE, (b["y"] + 0.5) * GRID_SCALE],
            "color": BUILDING_STYLE.get(b["kind"], {"color": [200, 200, 200]})["color"],
            "elevation": BUILDING_STYLE.get(b["kind"], {"height": 20})["height"],
            "kind": b["kind"],
            "building_id": b["building_id"],
        }
        for b in world["buildings"]
    ]

    ground_layer = pdk.Layer(
        "PolygonLayer",
        zone_data,
        get_polygon="polygon",
        get_fill_color="color",
        stroked=False,
        filled=True,
        pickable=False,
    )
    building_layer = pdk.Layer(
        "ColumnLayer",
        building_data,
        get_position="position",
        get_fill_color="color",
        get_elevation="elevation",
        radius=32,
        elevation_scale=1,
        pickable=True,
        auto_highlight=True,
    )
    view_state = pdk.ViewState(
        longitude=(width / 2) * GRID_SCALE,
        latitude=(height_dim / 2) * GRID_SCALE,
        zoom=16.3,
        pitch=52,
        bearing=24,
    )
    deck = pdk.Deck(
        layers=[ground_layer, building_layer],
        initial_view_state=view_state,
        map_provider=None,
        tooltip={"text": "{kind}\n{building_id}"},
    )
    st.pydeck_chart(deck, height=560)

    legend_items = {**ZONE_COLORS, **{k: v["color"] for k, v in BUILDING_STYLE.items()}}
    legend_cols = st.columns(len(legend_items))
    for col, (label, color) in zip(legend_cols, legend_items.items()):
        col.markdown(
            f'<div style="background:rgba({color[0]},{color[1]},{color[2]},0.9);'
            f'padding:3px 6px;border-radius:3px;font-size:11px;text-align:center">{label}</div>',
            unsafe_allow_html=True,
        )
    st.caption(f"{world['city_id']} — seed {world['seed']} — {width}x{height_dim} grid — drag to orbit, scroll to zoom")

# ============================================================================
# City Dashboard (SRS §30.5)
# ============================================================================
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

    st.subheader("Trends over time")
    series = pd.DataFrame(api_get("/simulation/metrics-timeseries"))
    if len(series) > 1:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.altair_chart(
                alt.Chart(series)
                .mark_line(color="#e05a5a", point=True)
                .encode(
                    x=alt.X("tick:Q", title="Day"),
                    y=alt.Y("food_price_index:Q", title="Food price index"),
                    tooltip=["tick", "food_price_index"],
                )
                .properties(height=220, title="Food price index over time"),
                use_container_width=True,
            )
            st.altair_chart(
                alt.Chart(series)
                .mark_area(color="#5a9be0", opacity=0.5, line={"color": "#5a9be0"})
                .encode(
                    x=alt.X("tick:Q", title="Day"),
                    y=alt.Y("population:Q", title="Population"),
                    tooltip=["tick", "population"],
                )
                .properties(height=220, title="Population over time"),
                use_container_width=True,
            )
        with chart_col2:
            employment_df = series.melt(
                id_vars=["tick"], value_vars=["employed", "active_businesses"], var_name="metric", value_name="value"
            )
            st.altair_chart(
                alt.Chart(employment_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("tick:Q", title="Day"),
                    y=alt.Y("value:Q", title="Count"),
                    color=alt.Color("metric:N", title=None, scale=alt.Scale(range=["#6ee06e", "#e0c05a"])),
                    tooltip=["tick", "metric", "value"],
                )
                .properties(height=220, title="Employment & active businesses"),
                use_container_width=True,
            )
            volume = pd.DataFrame(api_get("/simulation/event-volume"))
            if len(volume):
                by_tick = volume.groupby("tick", as_index=False)["count"].sum()
                st.altair_chart(
                    alt.Chart(by_tick)
                    .mark_bar(color="#9a7ae0")
                    .encode(
                        x=alt.X("tick:Q", title="Day"),
                        y=alt.Y("count:Q", title="Events"),
                        tooltip=["tick", "count"],
                    )
                    .properties(height=220, title="Event volume per day"),
                    use_container_width=True,
                )
    else:
        st.caption("Advance the simulation a few ticks to see trends.")

    st.json(status["policies"] or {"food_subsidy": 0, "tax_rate": 0.15, "interest_rate": 0.05})

# ============================================================================
# Citizens (SRS §30.2)
# ============================================================================
with tabs[2]:
    citizens_df = pd.DataFrame(api_get("/citizens"))
    st.dataframe(
        citizens_df[["citizen_id", "name", "age", "occupation", "employer_id", "salary", "savings", "stress"]],
        use_container_width=True,
        height=220,
    )

    st.subheader("Population statistics")
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    with stat_col1:
        st.altair_chart(
            alt.Chart(citizens_df)
            .mark_bar(color="#6ea8e0")
            .encode(
                x=alt.X("age:Q", bin=alt.Bin(maxbins=20), title="Age"),
                y=alt.Y("count():Q", title="Citizens"),
            )
            .properties(height=200, title="Age distribution"),
            use_container_width=True,
        )
    with stat_col2:
        occ_counts = citizens_df["occupation"].value_counts().reset_index()
        occ_counts.columns = ["occupation", "count"]
        st.altair_chart(
            alt.Chart(occ_counts)
            .mark_bar(color="#e0a05a")
            .encode(
                x=alt.X("count:Q", title="Citizens"),
                y=alt.Y("occupation:N", sort="-x", title=None),
                tooltip=["occupation", "count"],
            )
            .properties(height=200, title="Occupation breakdown"),
            use_container_width=True,
        )
    with stat_col3:
        citizens_df["net_worth"] = citizens_df["savings"] - citizens_df["debt"]
        st.altair_chart(
            alt.Chart(citizens_df)
            .mark_bar(color="#7ae09a")
            .encode(
                x=alt.X("net_worth:Q", bin=alt.Bin(maxbins=20), title="Net worth"),
                y=alt.Y("count():Q", title="Citizens"),
            )
            .properties(height=200, title="Wealth distribution"),
            use_container_width=True,
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

# ============================================================================
# Households (SRS §30.3)
# ============================================================================
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
    households_df = pd.DataFrame(rows)
    st.dataframe(households_df, use_container_width=True, height=250)

    hh_col1, hh_col2 = st.columns(2)
    with hh_col1:
        st.altair_chart(
            alt.Chart(households_df)
            .mark_circle(size=90, color="#e08a5a", opacity=0.75)
            .encode(
                x=alt.X("total_savings:Q", title="Total household savings"),
                y=alt.Y("avg_stress:Q", title="Average financial stress"),
                size=alt.Size("members:Q", title="Members"),
                tooltip=["household_id", "members", "total_savings", "avg_stress"],
            )
            .properties(height=260, title="Savings vs. stress (bubble size = household size)"),
            use_container_width=True,
        )
    with hh_col2:
        st.altair_chart(
            alt.Chart(households_df)
            .mark_bar(color="#5ae0c0")
            .encode(
                x=alt.X("avg_stress:Q", bin=alt.Bin(maxbins=15), title="Average financial stress"),
                y=alt.Y("count():Q", title="Households"),
            )
            .properties(height=260, title="Household stress distribution"),
            use_container_width=True,
        )

# ============================================================================
# Businesses (SRS §30.4)
# ============================================================================
with tabs[4]:
    businesses_df = pd.DataFrame(api_get("/businesses"))
    st.dataframe(businesses_df, use_container_width=True, height=250)
    employer_ids = sorted(businesses_df["business_id"].tolist()) if len(businesses_df) else []

    if len(businesses_df):
        biz_col1, biz_col2 = st.columns(2)
        with biz_col1:
            industry_counts = businesses_df["industry"].value_counts().reset_index()
            industry_counts.columns = ["industry", "count"]
            st.altair_chart(
                alt.Chart(industry_counts)
                .mark_arc(innerRadius=50)
                .encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color("industry:N", title="Industry"),
                    tooltip=["industry", "count"],
                )
                .properties(height=260, title="Businesses by industry"),
                use_container_width=True,
            )
        with biz_col2:
            top_businesses = businesses_df.sort_values("cash", ascending=False)
            st.altair_chart(
                alt.Chart(top_businesses)
                .mark_bar()
                .encode(
                    x=alt.X("cash:Q", title="Cash"),
                    y=alt.Y("business_id:N", sort="-x", title=None),
                    color=alt.Color("active:N", title="Active", scale=alt.Scale(range=["#e05a5a", "#5ae08a"])),
                    tooltip=["business_id", "industry", "cash", "profit", "active"],
                )
                .properties(height=260, title="Cash on hand by business"),
                use_container_width=True,
            )

# ============================================================================
# Events & Causality (SRS §30.6, §22-23)
# ============================================================================
with tabs[5]:
    events_df = pd.DataFrame(api_get("/events", limit=500))
    if len(events_df):
        ev_col1, ev_col2 = st.columns(2)
        with ev_col1:
            type_counts = events_df["event_type"].value_counts().reset_index()
            type_counts.columns = ["event_type", "count"]
            st.altair_chart(
                alt.Chart(type_counts)
                .mark_bar(color="#8a7ae0")
                .encode(
                    x=alt.X("count:Q", title="Count"),
                    y=alt.Y("event_type:N", sort="-x", title=None),
                    tooltip=["event_type", "count"],
                )
                .properties(height=280, title="Event type breakdown (last 500)"),
                use_container_width=True,
            )
        with ev_col2:
            by_tick = events_df.groupby("simulation_tick", as_index=False).size()
            st.altair_chart(
                alt.Chart(by_tick)
                .mark_bar(color="#5ac0e0")
                .encode(
                    x=alt.X("simulation_tick:Q", title="Day"),
                    y=alt.Y("size:Q", title="Events"),
                    tooltip=["simulation_tick", "size"],
                )
                .properties(height=280, title="Event volume per day (last 500)"),
                use_container_width=True,
            )

    st.dataframe(events_df, use_container_width=True, height=250)

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

# ============================================================================
# AI Agents (SRS §30.7)
# ============================================================================
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

# ============================================================================
# Alternate Timelines (SRS §27-29)
# ============================================================================
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
            metrics_a = comparison["simulation_a"]["metrics"]
            metrics_b = comparison["simulation_b"]["metrics"]
            compare_rows = []
            for key in metrics_a:
                if key == "tick":
                    continue
                compare_rows.append({"metric": key, "timeline": a, "value": metrics_a[key]})
                compare_rows.append({"metric": key, "timeline": b, "value": metrics_b[key]})
            compare_df = pd.DataFrame(compare_rows)
            st.altair_chart(
                alt.Chart(compare_df)
                .mark_bar()
                .encode(
                    x=alt.X("timeline:N", title=None),
                    y=alt.Y("value:Q"),
                    color=alt.Color("timeline:N", scale=alt.Scale(range=["#5a9be0", "#e0a05a"])),
                    column=alt.Column("metric:N", title=None),
                    tooltip=["metric", "timeline", "value"],
                )
                .properties(height=240, width=120),
                use_container_width=False,
            )
            st.markdown("**Divergent events**")
            div_col1, div_col2 = st.columns(2)
            with div_col1:
                st.caption(a)
                st.dataframe(pd.DataFrame(comparison["divergent_events"][a]), use_container_width=True, height=200)
            with div_col2:
                st.caption(b)
                st.dataframe(pd.DataFrame(comparison["divergent_events"][b]), use_container_width=True, height=200)
    else:
        st.caption("Branch at least once to compare timelines.")

    st.markdown("**Activate a simulation** (existing tick/disaster/AI actions act on whichever is active)")
    if sim_ids:
        activate_id = st.selectbox("Activate", sim_ids, key="activate_select")
        if st.button("Set active"):
            resp = api_post(f"/simulation/activate/{activate_id}")
            st.write(resp.json() if resp.ok else resp.text)
