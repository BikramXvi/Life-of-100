"""End-to-end FastAPI smoke tests. Run without any external infra (Postgres/
Kafka/Gemini) — the API must degrade gracefully when they're unavailable
(SRS §16/§17/§34), and all Gemini calls are mocked (protects the free-tier
quota, matches the rest of the suite)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from life100.api.main import app

client = TestClient(app)


def test_full_demo_flow_without_external_infra():
    start_resp = client.post("/simulation/start", json={"seed": 847291, "population": 20})
    assert start_resp.status_code == 200
    body = start_resp.json()
    assert body["population"] == 20
    # Postgres isn't necessarily running in this test environment - the API
    # must still work either way.
    assert body["postgres_bootstrap"] in ("loaded", "unavailable")

    citizens = client.get("/citizens").json()
    assert len(citizens) == 20
    citizen_id = citizens[0]["citizen_id"]

    detail = client.get(f"/citizens/{citizen_id}")
    assert detail.status_code == 200
    assert detail.json()["citizen_id"] == citizen_id

    assert client.get("/citizens/does_not_exist").status_code == 404

    businesses = client.get("/businesses").json()
    assert len(businesses) > 0
    business_id = businesses[0]["business_id"]
    assert client.get(f"/businesses/{business_id}").status_code == 200
    assert client.get("/businesses/does_not_exist").status_code == 404

    households = client.get("/households").json()
    assert len(households) > 0
    assert all(h["home_building_id"] for h in households)
    household_id = households[0]["household_id"]
    assert client.get(f"/households/{household_id}").status_code == 200
    assert client.get("/households/does_not_exist").status_code == 404

    drought_resp = client.post("/disasters/drought", json={"duration_ticks": 10})
    assert drought_resp.status_code == 200

    tick_resp = client.post("/simulation/tick", json={"ticks": 15})
    assert tick_resp.status_code == 200
    assert tick_resp.json()["tick"] == 15

    status = client.get("/simulation/status").json()
    assert status["food_price_index"] >= 1.0
    # civilization-level status bar fields (dashboard's persistent status bar)
    assert 0.0 <= status["unemployment_rate"] <= 1.0
    assert status["active_businesses"] >= 0
    assert status["health_incidents"] >= 0
    assert isinstance(status["active_disasters_detail"], dict)
    # `duration_ticks` on disasters means days (unchanged); a 15-hour advance
    # is under one day, so the 10-day drought above is still active here too
    # -- triggering flood alongside it (different disaster names, no
    # conflict) checks the detail dict is populated while disasters are active.
    client.post("/disasters/flood", json={})
    mid_status = client.get("/simulation/status").json()
    assert "flood" in mid_status["active_disasters_detail"]
    assert mid_status["active_disasters_detail"]["flood"]["magnitude"] is not None

    events = client.get("/events", params={"limit": 200}).json()
    assert len(events) > 0

    timeline = client.get(f"/citizens/{citizen_id}/timeline").json()
    assert isinstance(timeline, list)

    metrics = client.get("/observability/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["events_total"] >= 0

    reproducibility = client.get("/simulation/reproducibility")
    assert reproducibility.status_code == 200
    assert reproducibility.json()["seed"] == 847291

    world = client.get("/world").json()
    assert world["seed"] == 847291
    assert len(world["zones"]) == world["width"] * world["height"]
    assert any(b["kind"] == "home" for b in world["buildings"])

    experiment = client.post(
        "/experiments/run",
        json={
            "ticks": 5,
            "scenarios": [
                {"name": "World A - No Intervention", "disaster": "drought"},
                {"name": "World B - Food Subsidy", "disaster": "drought", "policies": {"food_subsidy": 0.5}},
            ],
        },
    )
    assert experiment.status_code == 200
    body = experiment.json()
    assert len(body["scenarios"]) == 2
    assert "control" in body
    # every resulting world got registered and is independently inspectable
    world_b_id = body["scenarios"][1]["simulation_id"]
    assert client.get("/simulation/list").json()["active_simulation_id"] is not None
    activate = client.post(f"/simulation/activate/{world_b_id}")
    assert activate.status_code == 200
    assert client.get("/citizens").status_code == 200

    sensitivity = client.post(
        "/experiments/sensitivity",
        json={"values": [0.1, 0.2, 0.3, 0.4], "ticks": 5},
    )
    assert sensitivity.status_code == 200
    sbody = sensitivity.json()
    assert sbody["parameter"] == "drought_severity"
    assert len(sbody["metrics_by_value"]) == 4
    assert set(sbody["tipping_points"]) == {
        "unemployment_rate",
        "business_failures",
        "avg_household_stress",
        "food_price_index",
        "health_incidents",
        "avg_household_wealth",
    }

    bad_sweep = client.post("/experiments/sensitivity", json={"parameter": "not_a_real_parameter"})
    assert bad_sweep.status_code == 400


def test_earthquake_and_flood_expose_damage_fraction_over_the_api():
    """Previously the API only accepted duration_ticks for these two --
    damage_fraction/affected_share were only reachable by calling
    trigger_earthquake()/trigger_flood() directly in Python, which is part
    of why the structural-collapse failure path went untested at any
    realistic magnitude for so long (see PROOF.md)."""
    client.post("/simulation/start", json={"seed": 847291, "population": 60})
    resp = client.post(
        "/disasters/earthquake",
        json={"duration_ticks": 10, "damage_fraction": 0.7, "affected_share": 0.5},
    )
    assert resp.status_code == 200
    resp = client.post(
        "/disasters/flood",
        json={"duration_ticks": 10, "damage_fraction": 0.5, "affected_share": 0.4},
    )
    assert resp.status_code == 200


def test_endpoints_require_a_started_simulation():
    # A process-wide singleton means this depends on test order in this
    # module; assert on the dependency's behavior directly instead.
    from life100.api.dependencies import get_engine
    from life100.api.state import state

    original = state.engine
    try:
        state.engine = None
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            get_engine()
    finally:
        state.engine = original


def test_ai_endpoints_use_mocked_gemini_never_call_live_api():
    client.post("/simulation/start", json={"seed": 847291, "population": 15})

    with patch("life100.agents.government.GeminiAgentClient") as mock_cls:
        mock_cls.return_value.generate_structured.return_value = {
            "action": "food_subsidy",
            "value": 0.2,
            "rationale": "Food prices have increased meaningfully this run.",
        }
        resp = client.post("/ai/government/propose")
    assert resp.status_code == 200
    assert resp.json()["approved"] is True

    citizen_id = client.get("/citizens").json()[0]["citizen_id"]

    with patch("life100.agents.historian.GeminiAgentClient") as mock_cls:
        mock_cls.return_value.generate_structured.return_value = {
            "answer": "No significant events yet for this citizen.",
            "cited_event_ids": [],
        }
        resp = client.post("/ai/historian/ask", json={"citizen_id": citizen_id, "question": "Why?"})
    assert resp.status_code == 200
    assert resp.json()["cited_event_ids"] == []
