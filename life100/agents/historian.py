"""Historian Agent. SRS §20.4, §24.

Answers "why did X happen to this citizen" questions using only the
citizen's real event history. The agent is required to cite the `event_id`
of every event its answer relies on, and this module independently checks
those citations against the evidence it actually handed the model —
`GroundingError` is raised if the model cites something that was never
provided, i.e. fabricated evidence (explicitly forbidden by SRS §20.4/§21).
"""

from __future__ import annotations

from typing import Any

from life100.agents.base import GeminiAgentClient
from life100.events.store import EventLog

HISTORIAN_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "cited_event_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "cited_event_ids"],
}

SYSTEM_INSTRUCTION = (
    "You are the Historian Agent for LIFE/100. Answer the question about this citizen "
    "using ONLY the evidence events listed below. Cite the event_id of every event your "
    "answer relies on in `cited_event_ids`. Never invent an event_id that was not given "
    "to you, and never state something as fact unless it is supported by the evidence."
)


class GroundingError(Exception):
    """The Historian's answer cited an event_id that was not part of the
    evidence it was given."""


def answer_question(
    citizen_id: str,
    question: str,
    log: EventLog,
    client: GeminiAgentClient | None = None,
    max_events: int = 20,
) -> dict[str, Any]:
    client = client or GeminiAgentClient()

    evidence = log.for_entity(citizen_id)[-max_events:]
    evidence_ids = {e.event_id for e in evidence}
    evidence_text = "\n".join(
        f"- [{e.event_id}] tick={e.simulation_tick} {e.event_type.value} payload={e.payload}" for e in evidence
    )

    prompt = (
        f"Citizen: {citizen_id}\n"
        f"Question: {question}\n\n"
        f"Evidence (real events only -- cite by event_id):\n"
        f"{evidence_text or '(no events found for this citizen)'}"
    )
    result = client.generate_structured(prompt, HISTORIAN_SCHEMA, SYSTEM_INSTRUCTION)

    cited = set(result.get("cited_event_ids", []))
    fabricated = cited - evidence_ids
    if fabricated:
        raise GroundingError(f"Historian cited event_id(s) not present in the evidence: {sorted(fabricated)}")

    return {
        "answer": result["answer"],
        "cited_event_ids": sorted(cited),
        "evidence_considered": len(evidence),
    }
