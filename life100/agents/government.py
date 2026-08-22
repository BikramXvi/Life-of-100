"""Government Agent. SRS §20.1.

Analyzes an economic snapshot and proposes one policy change. The proposal
never reaches the simulation directly — it always goes
proposed -> validated -> (accepted -> applied | rejected), each step
recorded as its own event (AI_DECISION_PROPOSED/ACCEPTED/REJECTED,
POLICY_CHANGED), so the safety boundary is visible in the event log itself.
"""

from __future__ import annotations

from typing import Any

from life100.agents.base import GeminiAgentClient
from life100.agents.validator import validate_policy_proposal
from life100.events.schemas import EventType
from life100.simulation.engine import SimulationEngine

POLICY_PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["food_subsidy", "tax_rate", "interest_rate"]},
        "value": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["action", "value", "rationale"],
}

SYSTEM_INSTRUCTION = (
    "You are the Government Agent for LIFE/100, a small digital-society simulation. "
    "Analyze the economic snapshot you are given and propose exactly ONE constrained "
    "policy action as JSON matching the response schema. You have no authority to apply "
    "changes yourself -- a separate validator checks every proposal before anything "
    "happens. Keep the rationale short, concrete, and tied to the numbers you were given."
)


def build_economic_snapshot(engine: SimulationEngine) -> dict[str, Any]:
    households = list(engine.households.values())
    avg_stress = sum(h.financial_stress for h in households) / len(households) if households else 0.0
    working_age = [c for c in engine.citizens.values() if c.is_working_age()]
    unemployed = [c for c in working_age if c.occupation == "unemployed"]

    return {
        "food_price_index": round(engine.food_price_index, 3),
        "average_household_financial_stress": round(avg_stress, 3),
        "unemployment_rate": round(len(unemployed) / len(working_age), 3) if working_age else 0.0,
        "active_disasters": sorted(engine.active_disasters.keys()),
        "current_policies": dict(engine.policies),
    }


def propose_and_apply_policy(engine: SimulationEngine, client: GeminiAgentClient | None = None) -> dict[str, Any]:
    client = client or GeminiAgentClient()
    snapshot = build_economic_snapshot(engine)

    prompt = (
        "Current economic snapshot of the society:\n"
        f"{snapshot}\n\n"
        "Propose one policy action to address the most pressing issue you see."
    )
    proposal = client.generate_structured(prompt, POLICY_PROPOSAL_SCHEMA, SYSTEM_INSTRUCTION)

    proposed_event = engine.emit(
        EventType.AI_DECISION_PROPOSED,
        source_entity="government_agent",
        source_type="ai_agent",
        payload={"proposal": proposal, "snapshot": snapshot},
    )

    result = validate_policy_proposal(proposal)

    if not result.approved:
        engine.emit(
            EventType.AI_DECISION_REJECTED,
            source_entity="government_agent",
            source_type="ai_agent",
            payload={"proposal": proposal, "reason": result.reason, "proposed_event_id": proposed_event.event_id},
        )
        return {"approved": False, "proposal": proposal, "reason": result.reason}

    engine.emit(
        EventType.AI_DECISION_ACCEPTED,
        source_entity="government_agent",
        source_type="ai_agent",
        payload={"proposal": proposal, "reason": result.reason, "proposed_event_id": proposed_event.event_id},
    )
    applied_event = engine.emit(
        EventType.POLICY_CHANGED,
        source_entity="government",
        source_type="government",
        payload={"policy": proposal["action"], "value": proposal["value"], "rationale": proposal["rationale"]},
    )
    return {"approved": True, "proposal": proposal, "reason": result.reason, "event_id": applied_event.event_id}
