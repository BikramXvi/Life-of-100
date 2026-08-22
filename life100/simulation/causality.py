"""Causal chain tracing. SRS §22 (Explainability Engine), §23 (Causal Graph).

Traces only *explicit* causal links that were recorded at the moment an
event was emitted (`payload["caused_by"]`, `payload["proposed_event_id"]`) —
this is deliberately not a heuristic/inferred graph. The same discipline the
Historian Agent applies to its citations (agents/historian.py: cite only
real evidence, never fabricate) applies here: a cause is only shown if it
was actually recorded, not guessed.
"""

from __future__ import annotations

from life100.events.schemas import Event
from life100.events.store import EventLog

CAUSE_LINK_KEYS = ("caused_by", "caused_by_disaster_event_id", "proposed_event_id")


def _linked_cause_id(event: Event) -> str | None:
    for key in CAUSE_LINK_KEYS:
        value = event.payload.get(key)
        if value:
            return value
    return None


def trace_causes(log: EventLog, event_id: str, max_depth: int = 10) -> list[Event]:
    """Walk backward from `event_id` through explicit causal links.
    Returns the chain starting with `event_id` itself."""
    chain: list[Event] = []
    seen: set[str] = set()
    current = log.get(event_id)
    while current is not None and current.event_id not in seen and len(chain) < max_depth:
        seen.add(current.event_id)
        chain.append(current)
        next_id = _linked_cause_id(current)
        current = log.get(next_id) if next_id else None
    return chain


def trace_effects(log: EventLog, event_id: str) -> list[Event]:
    """Forward direction: every event that explicitly cites `event_id` as
    its cause."""
    return [e for e in log.all() if _linked_cause_id(e) == event_id]
