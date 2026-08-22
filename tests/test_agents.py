"""Agent/validator tests. All Gemini calls are mocked — no live API traffic
runs during `pytest` (protects the free-tier quota; see agents/base.py)."""

from unittest.mock import MagicMock

import pytest

from life100.agents import government, historian
from life100.agents.validator import validate_policy_proposal
from life100.events.schemas import EventType
from life100.simulation.business import generate_businesses
from life100.simulation.disasters import trigger_drought
from life100.simulation.economy import run_tick
from life100.simulation.engine import SimulationEngine
from life100.simulation.households import generate_population
from life100.simulation.world import WorldConfig, generate_world

SEED = 847291


def _build_engine(n: int = 30) -> SimulationEngine:
    world = generate_world(WorldConfig(seed=SEED))
    citizens, households = generate_population(SEED, n=n)
    businesses = generate_businesses(SEED, world, citizens)
    return SimulationEngine(world, citizens, households, businesses)


def test_validator_accepts_in_bounds_proposal():
    result = validate_policy_proposal(
        {"action": "food_subsidy", "value": 0.4, "rationale": "food prices are up sharply"}
    )
    assert result.approved


def test_validator_rejects_out_of_bounds_value():
    result = validate_policy_proposal({"action": "food_subsidy", "value": 5.0, "rationale": "too much subsidy"})
    assert not result.approved


def test_validator_rejects_unknown_action():
    result = validate_policy_proposal({"action": "declare_war", "value": 1, "rationale": "not a real policy lever"})
    assert not result.approved


def test_government_agent_proposal_accepted_and_applied():
    engine = _build_engine()
    trigger_drought(engine)
    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "action": "food_subsidy",
        "value": 0.3,
        "rationale": "Food price index has risen sharply due to the drought.",
    }

    outcome = government.propose_and_apply_policy(engine, client=mock_client)

    assert outcome["approved"] is True
    assert engine.policies["food_subsidy"] == 0.3
    assert any(e.event_type == EventType.AI_DECISION_PROPOSED for e in engine.log.all())
    assert any(e.event_type == EventType.AI_DECISION_ACCEPTED for e in engine.log.all())
    assert any(e.event_type == EventType.POLICY_CHANGED for e in engine.log.all())


def test_government_agent_rejected_proposal_never_reaches_state():
    engine = _build_engine()
    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "action": "food_subsidy",
        "value": 99.0,  # out of the validator's allowed range
        "rationale": "an extreme measure",
    }

    outcome = government.propose_and_apply_policy(engine, client=mock_client)

    assert outcome["approved"] is False
    assert "food_subsidy" not in engine.policies
    assert any(e.event_type == EventType.AI_DECISION_REJECTED for e in engine.log.all())
    assert not any(e.event_type == EventType.POLICY_CHANGED for e in engine.log.all())


def test_historian_grounds_answer_in_real_events():
    engine = _build_engine()
    trigger_drought(engine)
    for _ in range(15):
        run_tick(engine)

    job_lost_events = engine.log.of_type(EventType.JOB_LOST)
    assert job_lost_events, "test setup expects at least one JOB_LOST event"
    citizen_id = job_lost_events[0].source_entity

    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "answer": f"{citizen_id} lost their job due to business cost pressure following the drought.",
        "cited_event_ids": [job_lost_events[0].event_id],
    }

    result = historian.answer_question(
        citizen_id, "Why did this citizen lose their job?", engine.log, client=mock_client
    )
    assert result["cited_event_ids"] == [job_lost_events[0].event_id]


def test_historian_rejects_fabricated_citations():
    engine = _build_engine()
    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "answer": "Something happened.",
        "cited_event_ids": ["evt_does_not_exist"],
    }

    with pytest.raises(historian.GroundingError):
        historian.answer_question("cit_0001", "Why?", engine.log, client=mock_client)
