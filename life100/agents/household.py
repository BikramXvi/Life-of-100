"""Household Decision Agent. SRS §20.3.

Activated only for a *significant* citizen decision — job opportunities,
moving house, major loans, education, business investment — not the
everyday choices decisions.py already handles deterministically. Same
safety-boundary pattern as the other agents.
"""

from __future__ import annotations

import random
from typing import Any

from life100.agents.base import GeminiAgentClient
from life100.agents.validator import validate_household_decision
from life100.events.schemas import Event, EventType
from life100.simulation.engine import SimulationEngine

HOUSEHOLD_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["accept_job_offer", "take_major_loan", "move_house", "pursue_education", "decline"],
        },
        "amount": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["action", "amount", "rationale"],
}

SYSTEM_INSTRUCTION = (
    "You are the Household Decision Agent for LIFE/100, evaluating ONE significant decision "
    "for ONE citizen (not routine daily choices - those are handled deterministically "
    "elsewhere). Weigh the citizen's finances, goals, and personality, then propose exactly "
    "ONE action as JSON: 'accept_job_offer', 'take_major_loan' (amount = loan size, "
    "1000-20000), 'move_house', 'pursue_education', or 'decline' (do nothing). For "
    "non-loan actions set amount to 0 or 1. You have no authority to apply changes yourself."
)


def build_citizen_snapshot(citizen, engine: SimulationEngine) -> dict[str, Any]:
    household = engine.households.get(citizen.household_id) if citizen.household_id else None
    return {
        "citizen_id": citizen.citizen_id,
        "age": citizen.age,
        "occupation": citizen.occupation,
        "salary": citizen.salary,
        "savings": citizen.savings,
        "debt": citizen.debt,
        "credit_score": citizen.credit_score,
        "stress": citizen.stress,
        "risk_tolerance": citizen.personality.risk_tolerance,
        "goals": vars(citizen.goals) if citizen.goals else None,
        "household_financial_stress": household.financial_stress if household else None,
    }


def propose_and_apply_household_decision(
    engine: SimulationEngine,
    citizen_id: str,
    decision_context: str,
    client: GeminiAgentClient | None = None,
) -> dict[str, Any]:
    citizen = engine.citizens.get(citizen_id)
    if citizen is None:
        raise ValueError(f"citizen {citizen_id} not found")

    client = client or GeminiAgentClient()
    snapshot = build_citizen_snapshot(citizen, engine)
    prompt = (
        f"Decision context: {decision_context}\n\n"
        f"Citizen snapshot:\n{snapshot}\n\n"
        "Propose one action for this citizen's household to take."
    )
    proposal = client.generate_structured(prompt, HOUSEHOLD_DECISION_SCHEMA, SYSTEM_INSTRUCTION)

    proposed_event = engine.emit(
        EventType.AI_DECISION_PROPOSED,
        source_entity="household_agent",
        source_type="ai_agent",
        payload={"citizen_id": citizen_id, "proposal": proposal, "snapshot": snapshot},
    )

    result = validate_household_decision(proposal)
    if not result.approved:
        engine.emit(
            EventType.AI_DECISION_REJECTED,
            source_entity="household_agent",
            source_type="ai_agent",
            payload={"proposal": proposal, "reason": result.reason, "proposed_event_id": proposed_event.event_id},
        )
        return {"approved": False, "proposal": proposal, "reason": result.reason}

    accepted_event = engine.emit(
        EventType.AI_DECISION_ACCEPTED,
        source_entity="household_agent",
        source_type="ai_agent",
        payload={"proposal": proposal, "reason": result.reason, "proposed_event_id": proposed_event.event_id},
    )
    applied = _apply_household_decision(engine, citizen, proposal, caused_by=accepted_event.event_id)
    return {
        "approved": True,
        "proposal": proposal,
        "reason": result.reason,
        "event_ids": [e.event_id for e in applied],
    }


def _apply_household_decision(
    engine: SimulationEngine, citizen, proposal: dict[str, Any], caused_by: str | None = None
) -> list[Event]:
    action = proposal["action"]
    events: list[Event] = []
    rng = random.Random(engine.world.seed + engine.tick + hash(citizen.citizen_id) % 1000)

    if action == "accept_job_offer" and citizen.occupation == "unemployed":
        from life100.simulation.business import BASE_SALARY

        candidates = [b for b in engine.businesses.values() if b.active and b.headcount() < 8]
        if candidates:
            business = min(candidates, key=lambda b: b.headcount())
            salary = round(BASE_SALARY.get(business.industry, 1500.0) * rng.uniform(0.9, 1.1), 2)
            events.append(
                engine.emit(
                    EventType.JOB_STARTED,
                    source_entity=citizen.citizen_id,
                    source_type="citizen",
                    payload={
                        "business_id": business.business_id,
                        "occupation": business.industry,
                        "salary": salary,
                        "caused_by": caused_by,
                    },
                )
            )
    elif action == "take_major_loan":
        events.append(
            engine.emit(
                EventType.LOAN_CREATED,
                source_entity=citizen.citizen_id,
                source_type="citizen",
                payload={
                    "amount": proposal["amount"],
                    "interest_rate": engine.government.interest_rate,
                    "caused_by": caused_by,
                },
            )
        )
    elif action == "move_house":
        household = engine.households.get(citizen.household_id) if citizen.household_id else None
        if household:
            homes = [b for b in engine.world.buildings_of_kind("home") if b.building_id != household.home_building_id]
            if homes:
                new_home = rng.choice(homes)
                events.append(
                    engine.emit(
                        EventType.MOVED,
                        source_entity=citizen.citizen_id,
                        source_type="citizen",
                        payload={
                            "household_id": household.household_id,
                            "new_home_building_id": new_home.building_id,
                            "caused_by": caused_by,
                        },
                    )
                )
    elif action == "pursue_education":
        next_level = {"none": "secondary", "secondary": "university"}.get(citizen.education_level)
        if next_level:
            events.append(
                engine.emit(
                    EventType.SCHOOL_ATTENDED,
                    source_entity=citizen.citizen_id,
                    source_type="citizen",
                    payload={
                        "education_level": citizen.education_level,
                        "upgrade_to": next_level,
                        "caused_by": caused_by,
                    },
                )
            )
    # "decline" applies nothing further -- the AI_DECISION_ACCEPTED event
    # already recorded that the household considered and declined to act.

    return events
