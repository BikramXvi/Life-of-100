"""Business Agent. SRS §20.2.

Analyzes one business's demand/revenue/inventory/costs/employees/loans and
proposes exactly one action. Same safety-boundary pattern as the Government
Agent (agents/government.py): proposed -> validated -> (accepted -> applied
| rejected), each step its own event.
"""

from __future__ import annotations

from typing import Any

from life100.agents.base import GeminiAgentClient
from life100.agents.validator import validate_business_proposal
from life100.events.schemas import Event, EventType
from life100.simulation.business import BASE_SALARY
from life100.simulation.engine import SimulationEngine

BUSINESS_PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["hire", "fire", "expand", "contract", "take_loan"]},
        "amount": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["action", "amount", "rationale"],
}

SYSTEM_INSTRUCTION = (
    "You are the Business Agent for LIFE/100, reasoning about ONE specific business. "
    "Analyze the snapshot you are given and propose exactly ONE action as JSON matching "
    "the response schema: 'hire'/'fire' (amount = headcount, 1-5), 'expand' (amount = cash "
    "invested, 500-20000), 'contract' (amount = fraction of cash shed, 0.05-0.5), or "
    "'take_loan' (amount = loan size, 500-20000). You have no authority to apply changes "
    "yourself -- a validator checks every proposal first."
)


def build_business_snapshot(business, engine: SimulationEngine) -> dict[str, Any]:
    return {
        "business_id": business.business_id,
        "industry": business.industry,
        "headcount": business.headcount(),
        "cash": business.cash,
        "revenue": business.revenue,
        "expenses": business.expenses,
        "profit": business.profit,
        "debt": business.debt,
        "active": business.active,
        "food_price_index": round(engine.food_price_index, 3),
    }


def propose_and_apply_business_action(
    engine: SimulationEngine, business_id: str, client: GeminiAgentClient | None = None
) -> dict[str, Any]:
    business = engine.businesses.get(business_id)
    if business is None:
        raise ValueError(f"business {business_id} not found")

    client = client or GeminiAgentClient()
    snapshot = build_business_snapshot(business, engine)
    prompt = f"Business snapshot:\n{snapshot}\n\nPropose one action to improve this business's position."
    proposal = client.generate_structured(prompt, BUSINESS_PROPOSAL_SCHEMA, SYSTEM_INSTRUCTION)

    proposed_event = engine.emit(
        EventType.AI_DECISION_PROPOSED,
        source_entity="business_agent",
        source_type="ai_agent",
        payload={"business_id": business_id, "proposal": proposal, "snapshot": snapshot},
    )

    result = validate_business_proposal(business, proposal)
    if not result.approved:
        engine.emit(
            EventType.AI_DECISION_REJECTED,
            source_entity="business_agent",
            source_type="ai_agent",
            payload={"proposal": proposal, "reason": result.reason, "proposed_event_id": proposed_event.event_id},
        )
        return {"approved": False, "proposal": proposal, "reason": result.reason}

    accepted_event = engine.emit(
        EventType.AI_DECISION_ACCEPTED,
        source_entity="business_agent",
        source_type="ai_agent",
        payload={"proposal": proposal, "reason": result.reason, "proposed_event_id": proposed_event.event_id},
    )
    applied = _apply_business_action(engine, business, proposal, caused_by=accepted_event.event_id)
    return {"approved": True, "proposal": proposal, "reason": result.reason, "event_ids": [e.event_id for e in applied]}


def _apply_business_action(
    engine: SimulationEngine, business, proposal: dict[str, Any], caused_by: str | None = None
) -> list[Event]:
    action = proposal["action"]
    amount = proposal["amount"]
    events: list[Event] = []

    if action == "hire":
        candidates = [
            c
            for c in engine.citizens.values()
            if c.alive and c.is_working_age() and c.occupation == "unemployed"
        ]
        base_salary = BASE_SALARY.get(business.industry, 1500.0)
        for citizen in candidates[: int(amount)]:
            events.append(
                engine.emit(
                    EventType.JOB_STARTED,
                    source_entity=citizen.citizen_id,
                    source_type="citizen",
                    payload={
                        "business_id": business.business_id,
                        "occupation": business.industry,
                        "salary": round(base_salary, 2),
                        "caused_by": caused_by,
                    },
                )
            )
    elif action == "fire":
        targets = sorted(
            business.employee_ids, key=lambda cid: len(engine.citizens[cid].employment_history)
        )[: int(amount)]
        for citizen_id in targets:
            events.append(
                engine.emit(
                    EventType.JOB_LOST,
                    source_entity=citizen_id,
                    source_type="citizen",
                    payload={
                        "business_id": business.business_id,
                        "reason": "business_agent_decision",
                        "caused_by": caused_by,
                    },
                )
            )
    elif action == "expand":
        events.append(
            engine.emit(
                EventType.BUSINESS_EXPANDED,
                source_entity=business.business_id,
                source_type="business",
                payload={"amount": amount, "caused_by": caused_by},
            )
        )
    elif action == "contract":
        events.append(
            engine.emit(
                EventType.BUSINESS_CONTRACTED,
                source_entity=business.business_id,
                source_type="business",
                payload={
                    "reason": "business_agent_decision",
                    "damage_fraction": amount,
                    "allow_failure": False,
                    "caused_by": caused_by,
                },
            )
        )
    elif action == "take_loan":
        events.append(
            engine.emit(
                EventType.LOAN_CREATED,
                source_entity=business.business_id,
                source_type="business",
                payload={"amount": amount, "interest_rate": engine.government.interest_rate, "caused_by": caused_by},
            )
        )

    return events
