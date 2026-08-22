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

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from life100.db.models import (
    AgentRow,
    BusinessRow,
    CitizenRow,
    EventRow,
    GovernmentRow,
    HouseholdRow,
    InfrastructureRow,
    RelationshipRow,
    SimulationStateRow,
)
from life100.events.schemas import Event, EventType
from life100.simulation.business import Business
from life100.simulation.citizens import Citizen
from life100.simulation.engine import SimulationEngine
from life100.simulation.households import Household

AGENT_MODULES = {
    "government_agent": "agents/government.py",
    "historian_agent": "agents/historian.py",
    "business_agent": "agents/business.py",
    "household_agent": "agents/household.py",
}


def bulk_upsert_initial_state(session: Session, engine: SimulationEngine) -> None:
    for citizen in engine.citizens.values():
        _upsert_citizen(session, citizen)
    for household in engine.households.values():
        _upsert_household(session, household)
    for business in engine.businesses.values():
        _upsert_business(session, business)
    for building in engine.world.buildings:
        _upsert_infrastructure(session, building, engine.world.city_id)

    # Relationships have no natural primary key (a graph edge, not an
    # entity) — this runs once at simulation start, so a full refresh
    # scoped to this simulation_id is simpler and just as correct as an
    # upsert here.
    session.execute(delete(RelationshipRow).where(RelationshipRow.simulation_id == engine.simulation_id))
    for citizen_id, edges in engine.relationships.items():
        for edge in edges:
            session.add(
                RelationshipRow(
                    simulation_id=engine.simulation_id,
                    citizen_id=citizen_id,
                    other_id=edge.other_id,
                    relationship_type=edge.relationship_type,
                    strength=edge.strength,
                    trust=edge.trust,
                    frequency=edge.frequency,
                )
            )

    gov_values = dict(
        simulation_id=engine.simulation_id,
        tax_rate=engine.government.tax_rate,
        interest_rate=engine.government.interest_rate,
        food_subsidy=engine.government.food_subsidy,
        healthcare_spending=engine.government.healthcare_spending,
        education_spending=engine.government.education_spending,
        infrastructure_spending=engine.government.infrastructure_spending,
        business_regulation=engine.government.business_regulation,
        environmental_regulation=engine.government.environmental_regulation,
    )
    gov_stmt = pg_insert(GovernmentRow).values(**gov_values)
    gov_stmt = gov_stmt.on_conflict_do_update(index_elements=[GovernmentRow.simulation_id], set_=gov_values)
    session.execute(gov_stmt)

    for agent_name, module_path in AGENT_MODULES.items():
        agent_values = dict(agent_name=agent_name, model="gemini-3.6-flash", module_path=module_path)
        agent_stmt = pg_insert(AgentRow).values(**agent_values)
        agent_stmt = agent_stmt.on_conflict_do_update(index_elements=[AgentRow.agent_name], set_=agent_values)
        session.execute(agent_stmt)

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


def _upsert_infrastructure(session: Session, building, city_id: str) -> None:
    values = dict(building_id=building.building_id, kind=building.kind, x=building.x, y=building.y, city_id=city_id)
    stmt = pg_insert(InfrastructureRow).values(**values)
    stmt = stmt.on_conflict_do_update(index_elements=[InfrastructureRow.building_id], set_=values)
    session.execute(stmt)


def insert_event(session: Session, event: Event) -> bool:
    """Idempotent insert into the durable event log.

    Returns True if this event was newly inserted, False if it was already
    present (duplicate-event handling, SRS §16/§19).

    Uses `RETURNING` rather than `result.rowcount` to detect whether a row
    was actually inserted: psycopg3 reports `rowcount == -1` (unknown) for
    `INSERT ... ON CONFLICT DO NOTHING` regardless of outcome, so checking
    `rowcount > 0` was silently always False — meaning every event the
    consumer ever processed looked like a duplicate, and
    `apply_event_to_state` never ran. `RETURNING` only yields a row for one
    that was actually inserted, which is the reliable signal.
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
        .returning(EventRow.event_id)
    )
    result = session.execute(stmt)
    inserted_id = result.scalar_one_or_none()
    session.commit()
    return inserted_id is not None


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

    elif event.event_type == EventType.POLICY_CHANGED:
        state = session.get(SimulationStateRow, event.simulation_id)
        if state:
            state.tick = event.simulation_tick
        government = session.get(GovernmentRow, event.simulation_id)
        policy_field = event.payload.get("policy")
        if government and policy_field and hasattr(government, policy_field):
            setattr(government, policy_field, float(event.payload["value"]))
        session.commit()

    elif event.event_type in (EventType.DISASTER_STARTED, EventType.DISASTER_ENDED):
        state = session.get(SimulationStateRow, event.simulation_id)
        if state:
            state.tick = event.simulation_tick
            session.commit()


def get_citizen(session: Session, citizen_id: str) -> CitizenRow | None:
    return session.get(CitizenRow, citizen_id)


def list_citizens(session: Session) -> list[CitizenRow]:
    return list(session.scalars(select(CitizenRow)))
