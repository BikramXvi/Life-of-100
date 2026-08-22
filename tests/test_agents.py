"""Agent/validator tests. All Gemini calls are mocked — no live API traffic
runs during `pytest` (protects the free-tier quota; see agents/base.py)."""

from unittest.mock import MagicMock

import pytest

from life100.agents import business, government, historian, household
from life100.agents.validator import validate_policy_proposal
from life100.events.schemas import EventType
from life100.simulation.disasters import trigger_drought
from life100.simulation.economy import run_tick
from life100.simulation.engine import SimulationEngine
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def _build_engine(n: int = 30) -> SimulationEngine:
    return bootstrap_simulation(SEED, population=n)


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


def test_business_agent_hire_action_accepted_and_creates_job_started():
    engine = _build_engine(n=100)
    # At this seed, labor demand happens to exceed supply (37 businesses x
    # up to 6 slots each vs ~65 working-age citizens), so nobody starts
    # unemployed -- free up one specific citizen so there's a real
    # candidate for the agent's hire action to find.
    target_business = next(iter(engine.businesses.values()))
    unemployable = next(
        c for c in engine.citizens.values() if c.is_working_age() and c.employer_id != target_business.business_id
    )
    if unemployable.employer_id:
        engine.businesses[unemployable.employer_id].employee_ids.remove(unemployable.citizen_id)
    unemployable.occupation = "unemployed"
    unemployable.employer_id = None
    unemployable.salary = 0.0

    headcount_before = target_business.headcount()

    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "action": "hire",
        "amount": 2,
        "rationale": "Demand is strong enough to support two more employees.",
    }
    outcome = business.propose_and_apply_business_action(engine, target_business.business_id, client=mock_client)

    assert outcome["approved"] is True
    assert target_business.headcount() >= headcount_before
    assert any(e.event_type == EventType.JOB_STARTED for e in engine.log.all())


def test_business_agent_rejects_firing_more_than_it_employs():
    engine = _build_engine()
    target_business = next(iter(engine.businesses.values()))

    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "action": "fire",
        "amount": 999,
        "rationale": "Cutting costs drastically.",
    }
    outcome = business.propose_and_apply_business_action(engine, target_business.business_id, client=mock_client)

    assert outcome["approved"] is False
    assert any(e.event_type == EventType.AI_DECISION_REJECTED for e in engine.log.all())


def test_household_agent_take_major_loan_accepted_and_applied():
    engine = _build_engine()
    citizen = next(iter(engine.citizens.values()))
    debt_before = citizen.debt

    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "action": "take_major_loan",
        "amount": 5000,
        "rationale": "Needs funds for an unexpected major household expense.",
    }
    outcome = household.propose_and_apply_household_decision(
        engine, citizen.citizen_id, "considering a major loan", client=mock_client
    )

    assert outcome["approved"] is True
    assert citizen.debt > debt_before
    assert any(e.event_type == EventType.LOAN_CREATED for e in engine.log.all())


def test_household_agent_rejects_out_of_bounds_loan():
    engine = _build_engine()
    citizen = next(iter(engine.citizens.values()))

    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "action": "take_major_loan",
        "amount": 999_999,
        "rationale": "Wants a huge loan.",
    }
    outcome = household.propose_and_apply_household_decision(
        engine, citizen.citizen_id, "considering a major loan", client=mock_client
    )

    assert outcome["approved"] is False
    assert any(e.event_type == EventType.AI_DECISION_REJECTED for e in engine.log.all())


def test_historian_rejects_fabricated_citations():
    engine = _build_engine()
    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "answer": "Something happened.",
        "cited_event_ids": ["evt_does_not_exist"],
    }

    with pytest.raises(historian.GroundingError):
        historian.answer_question("cit_0001", "Why?", engine.log, client=mock_client)
