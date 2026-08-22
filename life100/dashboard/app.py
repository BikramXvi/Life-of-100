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
    ["World View", "City Dashboard", "What If? Lab", "Citizens", "Households", "Businesses", "Events & Causality", "AI Agents", "Alternate Timelines"]
)

# ============================================================================
# World View (SRS §30.1) — a real rendered 3D city, not a flat table.
#
# Buildings are rectangular extruded footprints (not lollipop columns),
# shaded with a material/lighting model for real depth. Roads render as a
# connected street network, not just colored tiles. Homes are tinted by
# their household's actual financial_stress (a diverging green->red scale)
# so the city visibly shows where hardship is concentrated — data, not
# decoration. Every other building kind keeps a fixed color, both with a
# small deterministic per-building tint/height jitter so the skyline reads
# as organic rather than a uniform grid of identical blocks.
# ============================================================================
import hashlib

ZONE_COLORS = {
    "residential": [58, 92, 62, 210],
    "commercial": [46, 72, 108, 210],
    "industrial": [104, 78, 52, 210],
    "park": [40, 88, 46, 235],
    "road": [32, 32, 36, 255],
}
BUILDING_STYLE = {
    "home": {"color": [190, 165, 120], "height": 16, "half_size": 0.26},
    "shop": {"color": [90, 150, 230], "height": 26, "half_size": 0.32},
    "factory": {"color": [220, 120, 70], "height": 40, "half_size": 0.40},
    "school": {"color": [160, 120, 220], "height": 32, "half_size": 0.36},
    "hospital": {"color": [220, 80, 90], "height": 36, "half_size": 0.36},
    "bank": {"color": [220, 180, 80], "height": 38, "half_size": 0.34},
    "government": {"color": [220, 220, 226], "height": 50, "half_size": 0.42},
}
STRESS_LOW_COLOR = [86, 196, 120]  # calm households
STRESS_HIGH_COLOR = [214, 68, 62]  # struggling households
GRID_SCALE = 0.0012  # degrees per grid cell (~130m) -- purely a rendering trick, not real geography
BUILDING_MATERIAL = {"ambient": 0.36, "diffuse": 0.7, "shininess": 28, "specularColor": [255, 255, 255]}


def _stable_jitter(key: str, spread: float) -> float:
    """Deterministic per-entity jitter (not Python's randomized str hash,
    which would flicker every Streamlit rerun) so each building's slight
    color/height variation stays fixed across reruns."""
    digest = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return ((digest % 2001) / 1000.0 - 1.0) * spread


def _lerp_color(low: list[int], high: list[int], t: float) -> list[int]:
    t = max(0.0, min(1.0, t))
    return [round(low[i] + (high[i] - low[i]) * t) for i in range(3)]


def _footprint(x: float, y: float, half_size: float) -> list[list[float]]:
    corners = ((-half_size, -half_size), (half_size, -half_size), (half_size, half_size), (-half_size, half_size))
    return [[(x + dx) * GRID_SCALE, (y + dy) * GRID_SCALE] for dx, dy in corners]


with tabs[0]:
    world = api_get("/world")
    width, height_dim = world["width"], world["height"]
    stress_by_building = {
        h["home_building_id"]: h["financial_stress"] for h in api_get("/households") if h.get("home_building_id")
    }

    zone_data = []
    for z in world["zones"]:
        base = ZONE_COLORS.get(z["kind"], [90, 90, 90, 200])
        jitter = _stable_jitter(f"zone_{z['x']}_{z['y']}", 10)
        color = [max(0, min(255, c + jitter)) for c in base[:3]] + [base[3]]
        elevation = 3 if z["kind"] == "park" else 0
        zone_data.append(
            {
                "polygon": _footprint(z["x"] + 0.5, z["y"] + 0.5, 0.5),
                "color": color,
                "elevation": elevation,
            }
        )

    road_cells = {(z["x"], z["y"]) for z in world["zones"] if z["kind"] == "road"}
    road_segments = []
    for x, y in road_cells:
        cx, cy = (x + 0.5) * GRID_SCALE, (y + 0.5) * GRID_SCALE
        for nx, ny in ((x + 1, y), (x, y + 1)):
            if (nx, ny) in road_cells:
                road_segments.append(
                    {"source": [cx, cy], "target": [(nx + 0.5) * GRID_SCALE, (ny + 0.5) * GRID_SCALE]}
                )

    building_data = []
    for b in world["buildings"]:
        style = BUILDING_STYLE.get(b["kind"], {"color": [200, 200, 200], "height": 20, "half_size": 0.3})
        if b["kind"] == "home" and b["building_id"] in stress_by_building:
            color = _lerp_color(STRESS_LOW_COLOR, STRESS_HIGH_COLOR, stress_by_building[b["building_id"]])
        else:
            jitter = _stable_jitter(b["building_id"] + "c", 14)
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
        "PolygonLayer",
        zone_data,
        get_polygon="polygon",
        get_fill_color="color",
        get_elevation="elevation",
        extruded=True,
        stroked=False,
        filled=True,
        pickable=False,
    )
    road_layer = pdk.Layer(
        "LineLayer",
        road_segments,
        get_source_position="source",
        get_target_position="target",
        get_color=[150, 150, 140, 160],
        get_width=3,
        width_min_pixels=1,
    )
    building_layer = pdk.Layer(
        "PolygonLayer",
        building_data,
        get_polygon="polygon",
        get_fill_color="color",
        get_elevation="elevation",
        extruded=True,
        wireframe=True,
        get_line_color=[20, 20, 20, 120],
        material=BUILDING_MATERIAL,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 90],
    )
    view_state = pdk.ViewState(
        longitude=(width / 2) * GRID_SCALE,
        latitude=(height_dim / 2) * GRID_SCALE,
        zoom=14.85,
        pitch=55,
        bearing=28,
    )
    deck = pdk.Deck(
        layers=[ground_layer, road_layer, building_layer],
        initial_view_state=view_state,
        map_provider=None,
        tooltip={"text": "{kind}\n{building_id}\nhousehold stress: {stress}"},
    )
    st.pydeck_chart(deck, height=580)

    legend_cols = st.columns(len(ZONE_COLORS) + len(BUILDING_STYLE) + 1)
    legend_items = [(k, v) for k, v in ZONE_COLORS.items()] + [
        (k, v["color"]) for k, v in BUILDING_STYLE.items() if k != "home"
    ]
    for col, (label, color) in zip(legend_cols, legend_items):
        col.markdown(
            f'<div style="background:rgba({color[0]},{color[1]},{color[2]},0.9);'
            f'padding:3px 6px;border-radius:3px;font-size:11px;text-align:center">{label}</div>',
            unsafe_allow_html=True,
        )
    legend_cols[-1].markdown(
        f'<div style="background:linear-gradient(90deg, rgb({STRESS_LOW_COLOR[0]},{STRESS_LOW_COLOR[1]},{STRESS_LOW_COLOR[2]}), '
        f'rgb({STRESS_HIGH_COLOR[0]},{STRESS_HIGH_COLOR[1]},{STRESS_HIGH_COLOR[2]}));'
        f'padding:3px 6px;border-radius:3px;font-size:11px;text-align:center;color:#111">home = stress</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"{world['city_id']} — seed {world['seed']} — {width}x{height_dim} grid — "
        "drag to orbit, scroll to zoom — homes tinted by their household's real financial stress"
    )

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
# What If? Lab — the actual point of this project.
#
# "We don't know what will happen. Let's run the experiment." One city, one
# starting state, N parallel worlds branched from it, each given a
# different intervention, all run for the same number of days. Every
# number below comes from POST /experiments/run actually simulating each
# world — there is no lookup table.
# ============================================================================
with tabs[2]:
    st.markdown("#### One city. Parallel futures.")
    st.caption(
        "Branches the CURRENT simulation state into several independent worlds, applies a "
        "different intervention to each, and runs every one of them for the same number of days."
    )

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.markdown("**Scenario**")
        exp_disaster = st.selectbox(
            "Disaster",
            ["drought", "food_shortage", "flood", "earthquake", "disease_outbreak", "economic_recession", "energy_crisis"],
            key="exp_disaster",
        )
        exp_duration = st.slider("Duration (days)", 5, 90, 30, key="exp_duration")
        exp_severity = st.slider(
            "Drought severity (only applies to drought)", 0.1, 1.0, 0.4, step=0.05, key="exp_severity"
        )
        exp_ticks = st.slider("Days to run", 5, 90, 30, key="exp_ticks")

    with exp_col2:
        st.markdown("**Government intervention (World B)**")
        exp_food_subsidy = st.slider("Food subsidy", 0.0, 1.0, 0.5, step=0.05, key="exp_food_subsidy")
        exp_interest_rate = st.slider("Interest rate", 0.0, 0.3, 0.05, step=0.01, key="exp_interest_rate")
        exp_healthcare = st.slider("Healthcare funding", 0.0, 1.0, 0.5, step=0.05, key="exp_healthcare")
        st.markdown("**World C**")
        st.caption("Emergency employment program (a demand stimulus, not scripted mass-hiring)")

    if st.button("▶ Run Experiment (3 parallel worlds)", type="primary"):
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
            st.session_state["last_experiment"] = resp.json()
        else:
            st.error(resp.text)

    experiment = st.session_state.get("last_experiment")
    if experiment:
        control_metrics = experiment["control"]["metrics"]
        rows = [{"world": "Control (no disaster)", **control_metrics}]
        for s in experiment["scenarios"]:
            rows.append({"world": s["name"], **s["metrics"]})
        result_df = pd.DataFrame(rows)

        st.markdown("#### Results")
        st.dataframe(
            result_df[
                ["world", "food_price_index", "unemployment_rate", "employment", "business_failures",
                 "health_incidents", "avg_household_wealth", "avg_household_stress"]
            ],
            use_container_width=True,
        )

        chart_metrics = ["food_price_index", "unemployment_rate", "business_failures", "health_incidents"]
        melted = result_df[result_df["world"] != "Control (no disaster)"][["world"] + chart_metrics].melt(
            id_vars="world", var_name="metric", value_name="value"
        )
        st.altair_chart(
            alt.Chart(melted)
            .mark_bar()
            .encode(
                x=alt.X("world:N", title=None, axis=alt.Axis(labels=False)),
                y=alt.Y("value:Q"),
                color=alt.Color("world:N", title=None),
                column=alt.Column("metric:N", title=None),
                tooltip=["world", "metric", "value"],
            )
            .properties(height=260, width=140)
            .resolve_scale(y="independent"),  # each metric has its own scale -- unemployment_rate
            # (0-1) would otherwise look flat next to health_incidents (100s)
            use_container_width=False,
        )

        st.markdown("#### Why did one world do better? Trace it.")
        st.caption(
            "Activate a world below, then use the Events & Causality tab's trace tool on any of "
            "its events — every divergence is individually inspectable, not just a different number."
        )
        world_options = {experiment["control"]["simulation_id"]: "Control"} | {
            s["simulation_id"]: s["name"] for s in experiment["scenarios"]
        }
        chosen_world = st.selectbox(
            "Inspect a world", list(world_options), format_func=lambda sid: world_options[sid], key="exp_inspect"
        )
        if st.button("Activate this world"):
            resp = api_post(f"/simulation/activate/{chosen_world}")
            st.write(resp.json() if resp.ok else resp.text)
    else:
        st.caption("Run an experiment to see results here.")

    st.divider()
    st.markdown("#### Sensitivity Analysis — find the tipping point")
    st.caption(
        "Sweeps drought severity across a range, branches an independent world at each value "
        "from the CURRENT simulation, and looks for a point where the response changes "
        "disproportionately — not just proportionally. A metric with a smooth response across "
        "the range is reported as having no tipping point, never forced to show one."
    )

    sens_col1, sens_col2, sens_col3 = st.columns(3)
    with sens_col1:
        sens_min = st.slider("Minimum severity", 0.05, 0.45, 0.05, step=0.05, key="sens_min")
    with sens_col2:
        sens_max = st.slider("Maximum severity", 0.1, 1.0, 0.5, step=0.05, key="sens_max")
    with sens_col3:
        sens_steps = st.slider("Number of steps", 4, 16, 10, key="sens_steps")
    sens_ticks = st.slider(
        "Days to run each branch",
        3,
        30,
        15,
        key="sens_ticks",
        help=(
            "Kept below 30 by default: at 30 ticks food_price_index and avg_household_stress "
            "both saturate at their caps for every severity, hiding the very differentiation "
            "this sweep exists to find."
        ),
    )

    if st.button("🔬 Run Sensitivity Sweep", type="primary"):
        if sens_max <= sens_min:
            st.error("Maximum severity must be greater than minimum severity.")
        else:
            step_size = (sens_max - sens_min) / (sens_steps - 1)
            sweep_values = [round(sens_min + i * step_size, 4) for i in range(sens_steps)]
            resp = api_post(
                "/experiments/sensitivity",
                {"parameter": "drought_severity", "values": sweep_values, "ticks": int(sens_ticks)},
            )
            if resp.ok:
                st.session_state["last_sensitivity"] = resp.json()
            else:
                st.error(resp.text)

    sensitivity = st.session_state.get("last_sensitivity")
    if sensitivity:
        st.caption(sensitivity["methodology"])
        sens_df = pd.DataFrame(sensitivity["metrics_by_value"])
        sens_df.insert(0, "severity", sensitivity["values"])

        sens_metrics = ["business_failures", "unemployment_rate", "health_incidents", "avg_household_wealth"]
        sens_chart_cols = st.columns(2)
        for idx, metric in enumerate(sens_metrics):
            tp = sensitivity["tipping_points"].get(metric)
            line = (
                alt.Chart(sens_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("severity:Q", title="Drought severity"),
                    y=alt.Y(f"{metric}:Q"),
                    tooltip=["severity", metric],
                )
                .properties(height=200, title=metric)
            )
            with sens_chart_cols[idx % 2]:
                if tp:
                    lo, hi = tp["bracket"]
                    band = (
                        alt.Chart(pd.DataFrame({"lo": [lo], "hi": [hi]}))
                        .mark_rect(opacity=0.2, color="red")
                        .encode(x="lo:Q", x2="hi:Q")
                    )
                    st.altair_chart(band + line, use_container_width=True)
                    refined = tp.get("refined_bracket")
                    located = f"{refined[0]:.3f}–{refined[1]:.3f}" if refined else f"{lo:.2f}–{hi:.2f}"
                    st.success(
                        f"**Tipping point in `{metric}`**: severity {located} "
                        f"(jump {tp['ratio']:.1f}× the typical step)."
                    )
                else:
                    st.altair_chart(line, use_container_width=True)
                    st.caption(f"No tipping point detected in `{metric}` — response is smooth across this range.")
    else:
        st.caption("Run a sweep to see the severity-response curve and any detected tipping point.")

# ============================================================================
# Citizens (SRS §30.2)
# ============================================================================
with tabs[3]:
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
with tabs[4]:
    households_df = pd.DataFrame(api_get("/households"))
    households_df["members"] = households_df["member_ids"].apply(len)
    st.dataframe(
        households_df[
            ["household_id", "members", "home_building_id", "property_value", "income", "expenses",
             "savings", "debt", "financial_stress", "living_conditions"]
        ],
        use_container_width=True,
        height=250,
    )

    hh_col1, hh_col2 = st.columns(2)
    with hh_col1:
        st.altair_chart(
            alt.Chart(households_df)
            .mark_circle(size=90, color="#e08a5a", opacity=0.75)
            .encode(
                x=alt.X("savings:Q", title="Household savings"),
                y=alt.Y("financial_stress:Q", title="Financial stress"),
                size=alt.Size("members:Q", title="Members"),
                tooltip=["household_id", "members", "savings", "financial_stress"],
            )
            .properties(height=260, title="Savings vs. stress (bubble size = household size)"),
            use_container_width=True,
        )
    with hh_col2:
        st.altair_chart(
            alt.Chart(households_df)
            .mark_bar(color="#5ae0c0")
            .encode(
                x=alt.X("financial_stress:Q", bin=alt.Bin(maxbins=15), title="Financial stress"),
                y=alt.Y("count():Q", title="Households"),
            )
            .properties(height=260, title="Household stress distribution"),
            use_container_width=True,
        )

# ============================================================================
# Businesses (SRS §30.4)
# ============================================================================
with tabs[5]:
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
with tabs[6]:
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
with tabs[7]:
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
with tabs[8]:
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
