"""Append-only in-process event log.

This is the simulation engine's own source of truth for "what happened" —
always available within the running API process, independent of whether
Kafka/Postgres are reachable. The Kafka producer mirrors the same events out
to Redpanda -> the consumer worker -> Postgres -> DuckDB, which is the
"modern data engineering pipeline" this submission also has to demonstrate;
see WORKING_NOTES.md. The Historian agent reads from this log (or, once the
API is talking to Postgres, from there) — either way it only ever cites
`event_id`s that are really in the log.
"""

from __future__ import annotations

from life100.events.schemas import Event, EventType


class EventLog:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def append(self, event: Event) -> None:
        self._events.append(event)

    def all(self) -> list[Event]:
        return list(self._events)

    def recent(self, n: int = 50) -> list[Event]:
        return self._events[-n:]

    def for_entity(self, entity_id: str) -> list[Event]:
        return [e for e in self._events if e.source_entity == entity_id or e.payload.get("citizen_id") == entity_id]

    def of_type(self, event_type: EventType) -> list[Event]:
        return [e for e in self._events if e.event_type == event_type]

    def get(self, event_id: str) -> Event | None:
        for e in self._events:
            if e.event_id == event_id:
                return e
        return None

    def __len__(self) -> int:
        return len(self._events)
