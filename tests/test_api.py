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

    drought_resp = client.post("/disasters/drought", json={"duration_ticks": 10})
    assert drought_resp.status_code == 200

    tick_resp = client.post("/simulation/tick", json={"ticks": 15})
    assert tick_resp.status_code == 200
    assert tick_resp.json()["tick"] == 15

    status = client.get("/simulation/status").json()
    assert status["food_price_index"] >= 1.0

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
