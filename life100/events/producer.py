"""Event transport. SRS §16 — the simulation must never block waiting for
Kafka; it generates an event, hands it to an `EventProducer`, and moves on.

`InMemoryEventProducer` is the default and what tests use, so simulation and
economy logic is fully testable without any broker running (CLAUDE.md ground
rule 3 — testability without external infra). `KafkaEventProducer` talks to
Redpanda when the docker-compose stack is up; it never raises out of
`send()` — a broker being down degrades to "this event didn't get mirrored
to the stream" rather than "the simulation stopped".
"""

from __future__ import annotations

import logging
from typing import Protocol

from life100.events.schemas import Event

logger = logging.getLogger(__name__)

TOPIC_BY_SOURCE_TYPE = {
    "citizen": "citizens",
    "household": "families",
    "business": "businesses",
    "government": "government",
    "disaster": "disasters",
    "ai_agent": "ai-decisions",
}
DEFAULT_TOPIC = "system-events"


class EventProducer(Protocol):
    def send(self, event: Event) -> None: ...


class InMemoryEventProducer:
    """Default producer: appends to a local list. No I/O, always available."""

    def __init__(self) -> None:
        self.sent: list[Event] = []

    def send(self, event: Event) -> None:
        self.sent.append(event)


class KafkaEventProducer:
    """Fire-and-forget producer backed by Redpanda/Kafka.

    The `confluent_kafka` import is deferred to `__init__` so importing this
    module (or running the test suite) never requires the Kafka client
    library or a broker to be present.
    """

    def __init__(self, broker: str) -> None:
        from confluent_kafka import Producer  # deferred import, see docstring

        self._producer = Producer({"bootstrap.servers": broker})

    def send(self, event: Event) -> None:
        topic = TOPIC_BY_SOURCE_TYPE.get(event.source_type, DEFAULT_TOPIC)
        try:
            self._producer.produce(topic, value=event.model_dump_json().encode("utf-8"))
            self._producer.poll(0)  # non-blocking: serve delivery callbacks, don't wait
        except Exception:  # noqa: BLE001 — Kafka being unavailable must never stop the sim
            logger.warning("Kafka producer failed to send event %s", event.event_id, exc_info=True)

    def flush(self, timeout: float = 5.0) -> None:
        self._producer.flush(timeout)
