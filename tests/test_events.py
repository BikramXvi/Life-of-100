import pytest
from pydantic import ValidationError

from life100.events.schemas import Event, EventType
from life100.events.producer import InMemoryEventProducer
from life100.events.store import EventLog


def _make_event(**overrides) -> Event:
    fields = dict(
        event_id="evt_test_00001",
        event_type=EventType.JOB_LOST,
        simulation_id="sim_001",
        simulation_tick=1,
        simulation_time="YEAR_01_MONTH_01_DAY_01",
        source_entity="cit_0001",
        source_type="citizen",
        city_id="city_001",
        payload={"business_id": "biz_001", "reason": "test"},
    )
    fields.update(overrides)
    return Event(**fields)


def test_event_requires_all_srs_fields():
    event = _make_event()
    assert event.event_id
    assert event.schema_version == 1
    assert event.event_type == EventType.JOB_LOST
    assert event.payload["business_id"] == "biz_001"


def test_event_rejects_unknown_event_type():
    with pytest.raises(ValidationError):
        _make_event(event_type="NOT_A_REAL_EVENT_TYPE")


def test_event_is_immutable():
    event = _make_event()
    with pytest.raises(ValidationError):
        event.event_type = EventType.JOB_STARTED


def test_in_memory_producer_records_sent_events():
    producer = InMemoryEventProducer()
    event = _make_event()
    producer.send(event)
    assert producer.sent == [event]


def test_event_log_queries():
    log = EventLog()
    event = _make_event()
    log.append(event)
    assert log.get(event.event_id) == event
    assert event in log.for_entity("cit_0001")
    assert event in log.of_type(EventType.JOB_LOST)
    assert log.recent(1) == [event]
