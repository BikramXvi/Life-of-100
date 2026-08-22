"""The simulation engine — the only component allowed to mutate citizen,
household, or business state (CLAUDE.md ground rule 4, SRS §21). Everything
else (economy.py, disasters.py, the AI agents' validated proposals) works by
constructing an `Event` and calling `engine.emit(...)`; `emit` both records
the event (event log + producer) and applies its effect to state via the
handler table below. There is no other path to a state change.
"""

from __future__ import annotations

from typing import Callable

from life100.events.producer import EventProducer, InMemoryEventProducer
from life100.events.schemas import Event, EventType
from life100.events.store import EventLog
from life100.simulation.business import Business
from life100.simulation.citizens import Citizen
from life100.simulation.government import POLICY_FIELD_MAP, Government
from life100.simulation.households import Household
from life100.simulation.resources import Resources
from life100.simulation.world import World


class SimulationEngine:
    def __init__(
        self,
        world: World,
        citizens: list[Citizen],
        households: list[Household],
        businesses: list[Business],
        producer: EventProducer | None = None,
        simulation_id: str = "sim_001",
    ) -> None:
        self.world = world
        self.citizens: dict[str, Citizen] = {c.citizen_id: c for c in citizens}
        self.households: dict[str, Household] = {h.household_id: h for h in households}
        self.businesses: dict[str, Business] = {b.business_id: b for b in businesses}
        self.producer = producer or InMemoryEventProducer()
        self.log = EventLog()
        self.simulation_id = simulation_id

        self.tick = 0
        self._seq = 0

        # Economy-wide indicators the economy/disaster modules read and write
        # only through emitted events (see economy.py, disasters.py).
        self.food_price_index = 1.0
        self.active_disasters: dict[str, dict] = {}
        self.policies: dict[str, float] = {}
        self.government = Government()
        self.resources = Resources()
        self.relationships: dict[str, list] = {}  # citizen_id -> list["Relationship"], see social.py

    # -- event plumbing -----------------------------------------------

    def _next_event_id(self) -> str:
        self._seq += 1
        return f"evt_{self.simulation_id}_{self.tick:05d}_{self._seq:04d}"

    def _sim_time(self) -> str:
        year = self.tick // 365 + 1
        day_of_year = self.tick % 365
        month = day_of_year // 30 + 1
        day = day_of_year % 30 + 1
        return f"YEAR_{year:02d}_MONTH_{month:02d}_DAY_{day:02d}"

    def emit(self, event_type: EventType, source_entity: str, source_type: str, payload: dict) -> Event:
        """Build, log, publish, and apply one event. The only entry point
        for a state change anywhere in the simulation."""
        event = Event(
            event_id=self._next_event_id(),
            event_type=event_type,
            simulation_id=self.simulation_id,
            simulation_tick=self.tick,
            simulation_time=self._sim_time(),
            source_entity=source_entity,
            source_type=source_type,
            city_id=self.world.city_id,
            payload=payload,
        )
        self.log.append(event)
        self.producer.send(event)
        handler = _HANDLERS.get(event.event_type)
        if handler:
            handler(self, event)
        return event


# -- event application handlers ----------------------------------------
# Each handler is the *only* code allowed to mutate the corresponding piece
# of state. Keep these small and side-effect-only; cascading logic (what
# leads to an event being emitted in the first place) lives in economy.py /
# disasters.py / agents/validator.py instead.


def _apply_job_lost(engine: SimulationEngine, event: Event) -> None:
    citizen = engine.citizens.get(event.source_entity)
    if citizen is None:
        return
    business = engine.businesses.get(citizen.employer_id) if citizen.employer_id else None
    if business and citizen.citizen_id in business.employee_ids:
        business.employee_ids.remove(citizen.citizen_id)
    citizen.employment_history.append(f"lost:{citizen.employer_id}")
    citizen.employer_id = None
    citizen.occupation = "unemployed"
    citizen.salary = 0.0
    citizen.stress = min(1.0, citizen.stress + 0.2)


def _apply_business_failed(engine: SimulationEngine, event: Event) -> None:
    business = engine.businesses.get(event.source_entity)
    if business:
        business.active = False


def _apply_price_changed(engine: SimulationEngine, event: Event) -> None:
    if event.payload.get("good") == "food":
        engine.food_price_index = float(event.payload["new_index"])


def _apply_disaster_started(engine: SimulationEngine, event: Event) -> None:
    disaster_type = event.payload["disaster_type"]
    engine.active_disasters[disaster_type] = {
        "started_tick": engine.tick,
        "duration": event.payload.get("duration_ticks", 20),
    }


def _apply_disaster_ended(engine: SimulationEngine, event: Event) -> None:
    engine.active_disasters.pop(event.payload["disaster_type"], None)


def _apply_policy_changed(engine: SimulationEngine, event: Event) -> None:
    policy = event.payload["policy"]
    value = float(event.payload["value"])
    engine.policies[policy] = value
    field_name = POLICY_FIELD_MAP.get(policy)
    if field_name:
        setattr(engine.government, field_name, value)


def _noop(engine: SimulationEngine, event: Event) -> None:
    """AI_DECISION_* events are informational safety-boundary markers —
    they record that a proposal happened, was accepted, or was rejected, but
    carry no direct state effect of their own (SRS §21)."""


_HANDLERS: dict[EventType, Callable[[SimulationEngine, Event], None]] = {
    EventType.JOB_LOST: _apply_job_lost,
    EventType.BUSINESS_FAILED: _apply_business_failed,
    EventType.PRICE_CHANGED: _apply_price_changed,
    EventType.DISASTER_STARTED: _apply_disaster_started,
    EventType.DISASTER_ENDED: _apply_disaster_ended,
    EventType.POLICY_CHANGED: _apply_policy_changed,
    EventType.AI_DECISION_PROPOSED: _noop,
    EventType.AI_DECISION_ACCEPTED: _noop,
    EventType.AI_DECISION_REJECTED: _noop,
}
