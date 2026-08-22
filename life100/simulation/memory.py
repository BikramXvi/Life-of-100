"""Memory system. SRS §25.

Rather than maintaining a separately-stored memory list per citizen (which
would just be a second copy of facts already in the event log, at risk of
drifting out of sync), significant memories are a curated *view* over the
same event log the Historian Agent already queries — computed on demand,
always consistent with the actual history.
"""

from __future__ import annotations

from life100.events.schemas import EventType
from life100.simulation.engine import SimulationEngine

# EventType -> a human label, only for the "significant" subset SRS §25 names
SIGNIFICANT_EVENT_LABELS: dict[EventType, str] = {
    EventType.JOB_STARTED: "First job / new job",
    EventType.MARRIAGE: "Marriage",
    EventType.CHILD_BORN: "Birth of a child",
    EventType.CITIZEN_DIED: "Death of a family member",
    EventType.BUSINESS_FAILED: "Business failure",
    EventType.LOAN_DEFAULTED: "Major financial loss",
    EventType.PROPERTY_PURCHASED: "Major achievement",
    EventType.DIVORCE: "Divorce",
}


def get_memories(engine: SimulationEngine, citizen_id: str) -> list[dict]:
    """This citizen's significant events, in chronological order, plus the
    death of any recorded family member (spouse/parent/child) — SRS's own
    example list: "first job, marriage, birth of child, major financial
    loss, death of family member, business failure, major achievement"."""
    log = engine.log
    own_events = [e for e in log.for_entity(citizen_id) if e.event_type in SIGNIFICANT_EVENT_LABELS]

    # Family ties as recorded *in the death event itself* (life_events.py
    # snapshots them at time of death) rather than current live state,
    # which engine.py's handler mutates (a widow's spouse_id is cleared).
    def _was_family_of(death_event) -> bool:
        payload = death_event.payload
        return (
            payload.get("spouse_id") == citizen_id
            or citizen_id in payload.get("parent_ids", [])
            or citizen_id in payload.get("children_ids", [])
        )

    family_deaths = [e for e in log.of_type(EventType.CITIZEN_DIED) if _was_family_of(e)]

    memories = own_events + family_deaths
    memories.sort(key=lambda e: e.simulation_tick)
    return [
        {
            "event_id": e.event_id,
            "label": SIGNIFICANT_EVENT_LABELS.get(e.event_type, e.event_type.value),
            "event_type": e.event_type.value,
            "simulation_tick": e.simulation_tick,
            "simulation_time": e.simulation_time,
            "payload": e.payload,
        }
        for e in memories
    ]
