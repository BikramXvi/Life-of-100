"""Postgres read/write helpers.

Two distinct write paths, matching how a real event-driven system splits
"bootstrap" from "ongoing state changes":

- `bulk_upsert_initial_state` — called once when a simulation starts, to
  load the freshly generated world's citizens/households/businesses into
  Postgres directly. This is a simplification for the submission (SCOPE.md):
  the full SRS model would represent even initial population as
  `CITIZEN_BORN`/`BUSINESS_CREATED` events; here the *initial* snapshot is a
  direct bulk write, and everything from that point on goes through the
  event pipeline.
- `insert_event` + `apply_event_to_state` — used by the Kafka consumer
  (`life100.streaming.consumer`) for every event it reads off the stream:
  append to the durable event log (idempotent on `event_id`), then apply the
  same category of state delta the in-process `SimulationEngine` applied,
  but to the Postgres row instead of the in-memory dataclass.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from life100.db.models import BusinessRow, CitizenRow, EventRow, HouseholdRow, SimulationStateRow
from life100.events.schemas import Event, EventType
from life100.simulation.business import Business
from life100.simulation.citizens import Citizen
from life100.simulation.engine import SimulationEngine
from life100.simulation.households import Household


def bulk_upsert_initial_state(session: Session, engine: SimulationEngine) -> None:
    for citizen in engine.citizens.values():
        _upsert_citizen(session, citizen)
    for household in engine.households.values():
        _upsert_household(session, household)
    for business in engine.businesses.values():
        _upsert_business(session, business)

    stmt = (
        pg_insert(SimulationStateRow)
        .values(
            simulation_id=engine.simulation_id,
            seed=engine.world.seed,
            tick=engine.tick,
            food_price_index=engine.food_price_index,
        )
        .on_conflict_do_update(
            index_elements=[SimulationStateRow.simulation_id],
            set_={"seed": engine.world.seed, "tick": engine.tick, "food_price_index": engine.food_price_index},
        )
    )
    session.execute(stmt)
    session.commit()


def _upsert_citizen(session: Session, citizen: Citizen) -> None:
    values = dict(
        citizen_id=citizen.citizen_id,
        name=citizen.name,
        age=citizen.age,
        gender=citizen.gender,
        household_id=citizen.household_id,
        occupation=citizen.occupation,
        employer_id=citizen.employer_id,
        salary=citizen.salary,
        savings=citizen.savings,
        debt=citizen.debt,
        health_score=citizen.health_score,
        stress=citizen.stress,
        alive=citizen.alive,
    )
    stmt = pg_insert(CitizenRow).values(**values)
    stmt = stmt.on_conflict_do_update(index_elements=[CitizenRow.citizen_id], set_=values)
    session.execute(stmt)


def _upsert_household(session: Session, household: Household) -> None:
    values = dict(
        household_id=household.household_id,
        member_ids=household.member_ids,
        income=household.income,
        expenses=household.expenses,
        savings=household.savings,
        debt=household.debt,
        financial_stress=household.financial_stress,
    )
    stmt = pg_insert(HouseholdRow).values(**values)
    stmt = stmt.on_conflict_do_update(index_elements=[HouseholdRow.household_id], set_=values)
    session.execute(stmt)


def _upsert_business(session: Session, business: Business) -> None:
    values = dict(
        business_id=business.business_id,
        industry=business.industry,
        building_id=business.building_id,
        employee_ids=business.employee_ids,
        cash=business.cash,
        revenue=business.revenue,
        expenses=business.expenses,
        profit=business.profit,
        active=business.active,
    )
    stmt = pg_insert(BusinessRow).values(**values)
    stmt = stmt.on_conflict_do_update(index_elements=[BusinessRow.business_id], set_=values)
    session.execute(stmt)


def insert_event(session: Session, event: Event) -> bool:
    """Idempotent insert into the durable event log.

    Returns True if this event was newly inserted, False if it was already
    present (duplicate-event handling, SRS §16/§19).
    """
    stmt = (
        pg_insert(EventRow)
        .values(
            event_id=event.event_id,
            event_type=event.event_type.value,
            schema_version=event.schema_version,
            simulation_id=event.simulation_id,
            simulation_tick=event.simulation_tick,
            simulation_time=event.simulation_time,
            source_entity=event.source_entity,
            source_type=event.source_type,
            city_id=event.city_id,
            payload=event.payload,
        )
        .on_conflict_do_nothing(index_elements=[EventRow.event_id])
    )
    result = session.execute(stmt)
    session.commit()
    return result.rowcount > 0


def apply_event_to_state(session: Session, event: Event) -> None:
    """Apply the same category of state delta the in-process
    SimulationEngine applies, but against Postgres rows. Unknown citizens/
    businesses (e.g. consumer running before the bulk load lands) are
    skipped rather than erroring — malformed/out-of-order event handling
    (SRS §34)."""
    if event.event_type == EventType.JOB_LOST:
        citizen = session.get(CitizenRow, event.source_entity)
        if citizen is None:
            return
        business = session.get(BusinessRow, citizen.employer_id) if citizen.employer_id else None
        if business and citizen.citizen_id in (business.employee_ids or []):
            business.employee_ids = [cid for cid in business.employee_ids if cid != citizen.citizen_id]
        citizen.employer_id = None
        citizen.occupation = "unemployed"
        citizen.salary = 0.0
        citizen.stress = min(1.0, citizen.stress + 0.2)
        session.commit()

    elif event.event_type == EventType.BUSINESS_FAILED:
        business = session.get(BusinessRow, event.source_entity)
        if business:
            business.active = False
            session.commit()

    elif event.event_type == EventType.PRICE_CHANGED and event.payload.get("good") == "food":
        state = session.get(SimulationStateRow, event.simulation_id)
        if state:
            state.food_price_index = float(event.payload["new_index"])
            state.tick = event.simulation_tick
            session.commit()

    elif event.event_type in (EventType.DISASTER_STARTED, EventType.DISASTER_ENDED, EventType.POLICY_CHANGED):
        state = session.get(SimulationStateRow, event.simulation_id)
        if state:
            state.tick = event.simulation_tick
            session.commit()


def get_citizen(session: Session, citizen_id: str) -> CitizenRow | None:
    return session.get(CitizenRow, citizen_id)


def list_citizens(session: Session) -> list[CitizenRow]:
    return list(session.scalars(select(CitizenRow)))
