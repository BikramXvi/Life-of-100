"""Integration tests against a real Postgres — skipped automatically if one
isn't reachable (the rest of the suite needs no external infra; this file
is the exception, since it's specifically testing SQL behavior that a mock
can't catch). Run with `docker compose up postgres` for these to execute.

This file exists because of a real bug found via live testing, not unit
tests: `insert_event`'s duplicate check relied on `result.rowcount`, but
psycopg3 reports `rowcount == -1` for `INSERT ... ON CONFLICT DO NOTHING`
regardless of outcome — so every event looked like a duplicate and
`apply_event_to_state` silently never ran through the consumer path. No
amount of mocking would have caught this; it required a real database.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import OperationalError

from life100.db import crud
from life100.db.models import GovernmentRow
from life100.db.session import init_db, make_engine, make_session_factory
from life100.events.schemas import Event, EventType

TEST_DATABASE_URL = "postgresql+psycopg://life100:life100@localhost:5432/life100"


def _session_factory():
    engine = make_engine(TEST_DATABASE_URL)
    try:
        init_db(engine)
    except OperationalError:
        pytest.skip("Postgres not reachable at localhost:5432 (start it with `docker compose up postgres`)")
    return make_session_factory(engine)


def _make_event(event_id: str, **payload_overrides) -> Event:
    payload = {"policy": "tax_rate", "value": 0.33, "rationale": "test"}
    payload.update(payload_overrides)
    return Event(
        event_id=event_id,
        event_type=EventType.POLICY_CHANGED,
        simulation_id="sim_crud_test",
        simulation_tick=0,
        simulation_time="YEAR_01_MONTH_01_DAY_01",
        source_entity="government",
        source_type="government",
        city_id="city_001",
        payload=payload,
    )


def test_insert_event_reports_true_on_first_insert_false_on_duplicate():
    session_factory = _session_factory()
    event = _make_event("evt_crud_test_dup_check")

    with session_factory() as session:
        session.query(GovernmentRow).filter_by(simulation_id="sim_crud_test").delete()
        session.commit()
        first = crud.insert_event(session, event)
        second = crud.insert_event(session, event)  # same event_id again

    assert first is True, "a genuinely new event must be reported as inserted"
    assert second is False, "the same event_id again must be reported as a duplicate"


def test_apply_event_to_state_updates_government_on_real_insert():
    session_factory = _session_factory()
    event = _make_event("evt_crud_test_policy_apply", value=0.37)

    with session_factory() as session:
        gov_values = dict(simulation_id="sim_crud_test", tax_rate=0.15)
        session.merge(GovernmentRow(**gov_values))
        session.commit()

        inserted = crud.insert_event(session, event)
        assert inserted is True
        crud.apply_event_to_state(session, event)

    with session_factory() as session:
        row = session.get(GovernmentRow, "sim_crud_test")
        assert row.tax_rate == 0.37
