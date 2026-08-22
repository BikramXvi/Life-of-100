"""Counterfactual / Alternate History Engine. SRS §27-29.

`branch_simulation` deep-copies a running SimulationEngine's entire mutable
state into an independent new engine with its own simulation_id — history
up to the branch point is shared (identical objects, then diverging as each
branch's own subsequent ticks/events accumulate under its own id).
`compare_simulations` gives the SRS §28 metrics table; the divergent event
lists it returns are also the material for §29's butterfly-effect
tracing — pass any one of those event_ids to `GET /events/{id}/effects`
(simulation/causality.py) to see exactly how it propagated.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from life100.events.producer import InMemoryEventProducer
from life100.events.schemas import Event
from life100.simulation.engine import SimulationEngine


@dataclass
class BranchInfo:
    simulation_id: str
    parent_simulation_id: str
    branch_point_tick: int
    seed: int


def branch_simulation(parent: SimulationEngine, new_simulation_id: str) -> SimulationEngine:
    if new_simulation_id == parent.simulation_id:
        raise ValueError("a branch must have a different simulation_id from its parent")

    # Kafka producers hold a non-copyable native client; branches get a
    # fresh in-memory one regardless of what the parent used (a branch is a
    # what-if exploration, not something that needs its own broker traffic).
    original_producer = parent.producer
    parent.producer = None  # type: ignore[assignment]
    try:
        branch = copy.deepcopy(parent)
    finally:
        parent.producer = original_producer

    branch.producer = InMemoryEventProducer()
    branch.simulation_id = new_simulation_id
    branch.branch_info = BranchInfo(  # type: ignore[attr-defined]
        simulation_id=new_simulation_id,
        parent_simulation_id=parent.simulation_id,
        branch_point_tick=parent.tick,
        seed=parent.world.seed,
    )
    return branch


def _metrics(engine: SimulationEngine) -> dict:
    citizens = [c for c in engine.citizens.values() if c.alive]
    households = list(engine.households.values())
    working_age = [c for c in citizens if c.is_working_age()]
    unemployed = [c for c in working_age if c.occupation == "unemployed"]
    active_businesses = [b for b in engine.businesses.values() if b.active]

    total_wealth = sum(c.savings + c.assets - c.debt for c in citizens)
    avg_stress = sum(h.financial_stress for h in households) / len(households) if households else 0.0

    return {
        "tick": engine.tick,
        "population": len(citizens),
        "food_price_index": round(engine.food_price_index, 4),
        "unemployment_rate": round(len(unemployed) / len(working_age), 4) if working_age else 0.0,
        "average_wealth": round(total_wealth / len(citizens), 2) if citizens else 0.0,
        "business_count": len(active_businesses),
        "average_household_stress": round(avg_stress, 4),
    }


def compare_simulations(engine_a: SimulationEngine, engine_b: SimulationEngine) -> dict:
    divergent_a = [e for e in engine_a.log.all() if e.simulation_id == engine_a.simulation_id]
    divergent_b = [e for e in engine_b.log.all() if e.simulation_id == engine_b.simulation_id]

    return {
        "simulation_a": {"simulation_id": engine_a.simulation_id, "metrics": _metrics(engine_a)},
        "simulation_b": {"simulation_id": engine_b.simulation_id, "metrics": _metrics(engine_b)},
        "divergent_events": {
            engine_a.simulation_id: [_summarize(e) for e in divergent_a],
            engine_b.simulation_id: [_summarize(e) for e in divergent_b],
        },
    }


def _summarize(event: Event) -> dict:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "simulation_tick": event.simulation_tick,
        "source_entity": event.source_entity,
    }
