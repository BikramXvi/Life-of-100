"""Kafka (Redpanda) -> Postgres consumer worker. SRS §16, §19.

Runs as its own process (see docker/Dockerfile.worker): subscribes to every
topic the `EventProducer` publishes to, and for each message durably logs
the event (idempotent on `event_id`) then applies its state delta to
Postgres. If Postgres or Redpanda is briefly unavailable this worker simply
retries/backs off — it is intentionally decoupled from the simulation
process, which is the whole point of SRS §16 ("simulation must never block
on Kafka").
"""

from __future__ import annotations

import logging
import os
import time

from life100.db import crud
from life100.db.session import init_db, make_engine, make_session_factory
from life100.events.producer import TOPIC_BY_SOURCE_TYPE
from life100.events.schemas import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("life100.streaming.consumer")

TOPICS = sorted(set(TOPIC_BY_SOURCE_TYPE.values()) | {"system-events"})


def run(broker: str | None = None, database_url: str | None = None, poll_timeout: float = 1.0) -> None:
    from confluent_kafka import Consumer  # deferred import — see events/producer.py

    broker = broker or os.environ.get("KAFKA_BROKER", "localhost:19092")
    engine = make_engine(database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)

    consumer = Consumer(
        {
            "bootstrap.servers": broker,
            "group.id": "life100-postgres-sync",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe(TOPICS)
    logger.info("subscribed to topics: %s", TOPICS)

    try:
        while True:
            msg = consumer.poll(poll_timeout)
            if msg is None:
                continue
            if msg.error():
                logger.warning("consumer error: %s", msg.error())
                continue

            _handle_message(session_factory, msg.value())
    except KeyboardInterrupt:
        logger.info("shutting down consumer")
    finally:
        consumer.close()


def _handle_message(session_factory, raw: bytes) -> None:
    try:
        event = Event.model_validate_json(raw)
    except Exception:  # noqa: BLE001 — malformed-event handling (SRS §34): log and skip, never crash the worker
        logger.warning("dropping malformed event message", exc_info=True)
        return

    with session_factory() as session:
        inserted = crud.insert_event(session, event)
        if not inserted:
            logger.info("duplicate event %s ignored", event.event_id)
            return
        crud.apply_event_to_state(session, event)


if __name__ == "__main__":
    # Small startup delay so `docker compose up` doesn't race the broker
    # being ready before this container starts polling.
    time.sleep(float(os.environ.get("WORKER_STARTUP_DELAY", "0")))
    run()
