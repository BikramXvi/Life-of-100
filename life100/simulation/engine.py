"""The simulation engine — the only component allowed to mutate citizen,
household, or business state (CLAUDE.md ground rule 4, SRS §21). Everything
else (economy.py, disasters.py, the AI agents' validated proposals) works by
constructing an `Event` and calling `engine.emit(...)`; `emit` both records
the event (event log + producer) and applies its effect to state via the
handler table below. There is no other path to a state change.
"""

from __future__ import annotations

import time
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
        self.tick_timestamps: list[float] = []  # SRS §33/§36 observability: ticks/sec

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

    def current_simulation_time(self) -> str:
        """Public accessor for observability/reproducibility endpoints."""
        return self._sim_time()

    def _sim_time(self) -> str:
        year = self.tick // 365 + 1
        day_of_year = self.tick % 365
        month = day_of_year // 30 + 1
        day = day_of_year % 30 + 1
        return f"YEAR_{year:02d}_MONTH_{month:02d}_DAY_{day:02d}"

    def broad_disaster_multipliers(self) -> tuple[float, float]:
        """(cost_multiplier, demand_multiplier) aggregated across every
        currently-active disaster that isn't drought/food_shortage (those
        already act through food_price_index specifically). Lets
        economy.py apply energy-crisis-style cost shocks and disease/
        recession-style demand shocks generically, without one bespoke
        code path per disaster type."""
        cost_multiplier = 1.0
        demand_multiplier = 1.0
        for info in self.active_disasters.values():
            magnitude = info.get("magnitude", 0.0)
            if info.get("kind") == "broad_cost_shock":
                cost_multiplier *= 1.0 + magnitude
            elif info.get("kind") == "broad_demand_shock":
                demand_multiplier *= max(0.2, 1.0 - magnitude)
        return cost_multiplier, demand_multiplier

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


def _apply_business_contracted(engine: SimulationEngine, event: Event) -> None:
    business = engine.businesses.get(event.source_entity)
    if business is None or not business.active:
        return
    damage_fraction = float(event.payload.get("damage_fraction", 0.0))
    loss = round(business.cash * damage_fraction, 2)
    business.cash = round(business.cash - loss, 2)
    if event.payload.get("allow_failure") and business.cash <= 0:
        # A direct, single-level consequence of this event (structural
        # collapse), not a cascade computed over many ticks — emitting from
        # within a handler is fine here; engine.emit is plain recursion, not
        # shared mutable global state.
        engine.emit(
            EventType.BUSINESS_FAILED,
            source_entity=business.business_id,
            source_type="business",
            payload={"reason": f"{event.payload.get('reason', 'disaster')}_structural_failure"},
        )


def _apply_purchase(engine: SimulationEngine, event: Event) -> None:
    citizen = engine.citizens.get(event.source_entity)
    if citizen is None:
        return
    citizen.savings = round(citizen.savings - float(event.payload["amount"]), 2)


def _apply_school_attended(engine: SimulationEngine, event: Event) -> None:
    citizen = engine.citizens.get(event.source_entity)
    if citizen is None:
        return
    citizen.academic_performance = round(min(1.0, citizen.academic_performance + 0.01), 3)
    upgrade_to = event.payload.get("upgrade_to")
    if upgrade_to:
        citizen.education_level = upgrade_to


def _apply_health_impacted(engine: SimulationEngine, event: Event) -> None:
    citizen = engine.citizens.get(event.source_entity)
    if citizen is None:
        return
    citizen.health_score = round(max(0.05, citizen.health_score - float(event.payload.get("health_delta", 0.0))), 3)
    citizen.stress = round(min(1.0, citizen.stress + float(event.payload.get("stress_delta", 0.0))), 3)


def _apply_medical_visit(engine: SimulationEngine, event: Event) -> None:
    citizen = engine.citizens.get(event.source_entity)
    if citizen is None:
        return
    citizen.savings = round(citizen.savings - float(event.payload["cost"]), 2)
    citizen.health_score = round(min(1.0, citizen.health_score + 0.08), 3)
    citizen.stress = round(max(0.0, citizen.stress - 0.05), 3)
    citizen.healthcare_visits += 1
    citizen.medical_history.append(event.payload.get("reason", "checkup"))


def _apply_loan_created(engine: SimulationEngine, event: Event) -> None:
    amount = float(event.payload["amount"])
    if event.source_type == "business":
        business = engine.businesses.get(event.source_entity)
        if business is None:
            return
        was_inactive = not business.active
        business.cash = round(business.cash + amount, 2)
        business.debt = round(business.debt + amount, 2)
        if was_inactive and business.cash > 0:
            # A capital injection can bring a failed business back — found
            # via live-testing the Business Agent, which correctly proposed
            # a loan for an inactive business but nothing previously
            # reactivated it (SCOPE.md). Reopening is itself an event, not
            # a silent side effect of this one.
            business.active = True
            engine.emit(
                EventType.BUSINESS_EXPANDED,
                source_entity=business.business_id,
                source_type="business",
                payload={"amount": 0.0, "reason": "reopened_after_loan", "caused_by": event.event_id},
            )
        return
    citizen = engine.citizens.get(event.source_entity)
    if citizen is None:
        return
    citizen.savings = round(citizen.savings + amount, 2)
    citizen.debt = round(citizen.debt + amount, 2)


def _apply_loan_repaid(engine: SimulationEngine, event: Event) -> None:
    amount = float(event.payload["amount"])
    if event.source_type == "business":
        business = engine.businesses.get(event.source_entity)
        if business is None:
            return
        business.cash = round(business.cash - amount, 2)
        business.debt = round(max(0.0, business.debt - amount), 2)
        return
    citizen = engine.citizens.get(event.source_entity)
    if citizen is None:
        return
    citizen.savings = round(citizen.savings - amount, 2)
    citizen.debt = round(max(0.0, citizen.debt - amount), 2)


def _apply_business_expanded(engine: SimulationEngine, event: Event) -> None:
    business = engine.businesses.get(event.source_entity)
    if business is None:
        return
    business.cash = round(business.cash + float(event.payload.get("amount", 0.0)), 2)


def _apply_moved(engine: SimulationEngine, event: Event) -> None:
    household = engine.households.get(event.payload.get("household_id", ""))
    if household is None:
        return
    new_home = event.payload.get("new_home_building_id")
    if new_home:
        household.home_building_id = new_home


def _apply_job_started(engine: SimulationEngine, event: Event) -> None:
    citizen = engine.citizens.get(event.source_entity)
    business = engine.businesses.get(event.payload["business_id"])
    if citizen is None or business is None:
        return
    citizen.occupation = event.payload["occupation"]
    citizen.employer_id = business.business_id
    citizen.salary = float(event.payload["salary"])
    citizen.employment_history.append(f"hired:{business.business_id}")
    if citizen.citizen_id not in business.employee_ids:
        business.employee_ids.append(citizen.citizen_id)


def _apply_citizen_died(engine: SimulationEngine, event: Event) -> None:
    citizen = engine.citizens.get(event.source_entity)
    if citizen is None:
        return
    citizen.alive = False
    if citizen.employer_id:
        business = engine.businesses.get(citizen.employer_id)
        if business and citizen.citizen_id in business.employee_ids:
            business.employee_ids.remove(citizen.citizen_id)
    citizen.occupation = "deceased"
    citizen.employer_id = None
    citizen.salary = 0.0
    if citizen.spouse_id:
        spouse = engine.citizens.get(citizen.spouse_id)
        if spouse:
            spouse.marital_status = "widowed"
            spouse.spouse_id = None


def _apply_marriage(engine: SimulationEngine, event: Event) -> None:
    a = engine.citizens.get(event.payload["citizen_id"])
    b = engine.citizens.get(event.payload["spouse_id"])
    if a is None or b is None:
        return
    a.spouse_id, b.spouse_id = b.citizen_id, a.citizen_id
    a.marital_status = b.marital_status = "married"

    edges_a = engine.relationships.setdefault(a.citizen_id, [])
    edges_b = engine.relationships.setdefault(b.citizen_id, [])
    if not any(r.other_id == b.citizen_id and r.relationship_type == "family" for r in edges_a):
        from life100.simulation.social import Relationship

        edges_a.append(Relationship(a.citizen_id, b.citizen_id, "family", 0.9, 0.9, 0.9, history=["married"]))
        edges_b.append(Relationship(b.citizen_id, a.citizen_id, "family", 0.9, 0.9, 0.9, history=["married"]))

    # Merge into one household (SRS §6.3: marriage is a family event) -- b
    # moves into a's household.
    new_household = engine.households.get(a.household_id)
    old_household = engine.households.get(b.household_id)
    if new_household and old_household and old_household is not new_household:
        if b.citizen_id in old_household.member_ids:
            old_household.member_ids.remove(b.citizen_id)
        if b.citizen_id not in new_household.member_ids:
            new_household.member_ids.append(b.citizen_id)
        b.household_id = a.household_id
        if not old_household.member_ids:
            del engine.households[old_household.household_id]


def _apply_divorce(engine: SimulationEngine, event: Event) -> None:
    a = engine.citizens.get(event.payload["citizen_id"])
    b = engine.citizens.get(event.payload["spouse_id"])
    if a is None or b is None:
        return
    a.spouse_id = b.spouse_id = None
    a.marital_status = b.marital_status = "divorced"

    # b moves out into a new household of their own.
    old_household = engine.households.get(a.household_id)
    if old_household and b.citizen_id in old_household.member_ids:
        old_household.member_ids.remove(b.citizen_id)
        new_household_id = f"{old_household.household_id}_split_{event.simulation_tick}"
        new_household = Household(household_id=new_household_id, member_ids=[b.citizen_id])
        engine.households[new_household_id] = new_household
        b.household_id = new_household_id


def _apply_child_born(engine: SimulationEngine, event: Event) -> None:
    import random as _random

    from life100.simulation.citizens import Citizen, Personality
    from life100.simulation.social import Relationship

    payload = event.payload
    child_id = payload["citizen_id"]
    if child_id in engine.citizens:
        return
    rng = _random.Random(abs(hash(child_id)) % (2**32))
    child = Citizen(
        citizen_id=child_id,
        name=payload["name"],
        age=0,
        gender=payload["gender"],
        personality=Personality(
            risk_tolerance=round(rng.random(), 3),
            ambition=round(rng.random(), 3),
            patience=round(rng.random(), 3),
            social_tendency=round(rng.random(), 3),
        ),
        household_id=payload["household_id"],
        parent_ids=list(payload["parent_ids"]),
    )
    engine.citizens[child_id] = child
    engine.relationships.setdefault(child_id, [])

    household = engine.households.get(payload["household_id"])
    if household and child_id not in household.member_ids:
        household.member_ids.append(child_id)

    for parent_id in child.parent_ids:
        parent = engine.citizens.get(parent_id)
        if parent is None:
            continue
        if child_id not in parent.children_ids:
            parent.children_ids.append(child_id)
        engine.relationships.setdefault(parent_id, [])
        engine.relationships[parent_id].append(
            Relationship(parent_id, child_id, "family", 0.9, 0.9, 0.85, history=["formed as family"])
        )
        engine.relationships[child_id].append(
            Relationship(child_id, parent_id, "family", 0.9, 0.9, 0.85, history=["formed as family"])
        )


def _apply_relationship_changed(engine: SimulationEngine, event: Event) -> None:
    a_id, b_id = event.payload["citizen_id"], event.payload["other_id"]
    delta = float(event.payload.get("strength_delta", 0.0))
    for a, b in ((a_id, b_id), (b_id, a_id)):
        for rel in engine.relationships.get(a, []):
            if rel.other_id == b:
                rel.strength = round(min(1.0, max(0.0, rel.strength + delta)), 3)
                rel.last_interaction_tick = engine.tick
                rel.history.append(f"interaction@tick{engine.tick}")


def _apply_price_changed(engine: SimulationEngine, event: Event) -> None:
    if event.payload.get("good") == "food":
        engine.food_price_index = float(event.payload["new_index"])


def _apply_disaster_started(engine: SimulationEngine, event: Event) -> None:
    disaster_type = event.payload["disaster_type"]
    engine.active_disasters[disaster_type] = {
        "started_tick": engine.tick,
        "duration": event.payload.get("duration_ticks", 20),
        "kind": event.payload.get("kind"),  # broad_cost_shock | broad_demand_shock | None
        "magnitude": event.payload.get("magnitude", 0.0),
        "event_id": event.event_id,  # explainability: lets downstream events cite the real trigger
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
    EventType.BUSINESS_CONTRACTED: _apply_business_contracted,
    EventType.BUSINESS_EXPANDED: _apply_business_expanded,
    EventType.MOVED: _apply_moved,
    EventType.PRICE_CHANGED: _apply_price_changed,
    EventType.DISASTER_STARTED: _apply_disaster_started,
    EventType.DISASTER_ENDED: _apply_disaster_ended,
    EventType.POLICY_CHANGED: _apply_policy_changed,
    EventType.PURCHASE: _apply_purchase,
    EventType.HEALTH_IMPACTED: _apply_health_impacted,
    EventType.SCHOOL_ATTENDED: _apply_school_attended,
    EventType.MEDICAL_VISIT: _apply_medical_visit,
    EventType.LOAN_CREATED: _apply_loan_created,
    EventType.LOAN_REPAID: _apply_loan_repaid,
    EventType.JOB_STARTED: _apply_job_started,
    EventType.RELATIONSHIP_CHANGED: _apply_relationship_changed,
    EventType.CITIZEN_DIED: _apply_citizen_died,
    EventType.MARRIAGE: _apply_marriage,
    EventType.DIVORCE: _apply_divorce,
    EventType.CHILD_BORN: _apply_child_born,
    EventType.RESOURCE_EXTRACTED: _noop,
    EventType.AI_DECISION_PROPOSED: _noop,
    EventType.AI_DECISION_ACCEPTED: _noop,
    EventType.AI_DECISION_REJECTED: _noop,
}
