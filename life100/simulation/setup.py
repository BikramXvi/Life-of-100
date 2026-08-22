"""Single entry point for assembling a fresh simulation.

Consolidates what used to be duplicated across api/routers/simulation.py and
every test's `_build_engine` helper — world + population + businesses + home
assignment + the social graph, all from one seed. Alternate-history
branching (simulation/alternate_history.py) also starts from this.
"""

from __future__ import annotations

import random

from life100.events.producer import EventProducer
from life100.simulation.business import generate_businesses
from life100.simulation.engine import SimulationEngine
from life100.simulation.households import Household, generate_population
from life100.simulation.social import generate_relationships
from life100.simulation.world import World, WorldConfig, generate_world


def assign_homes(seed: int, world: World, households: list[Household]) -> None:
    """Deterministically assign each household a home building from the
    world's housing stock (cycling if there are more households than
    homes)."""
    rng = random.Random(seed)
    homes = list(world.buildings_of_kind("home"))
    if not homes:
        return
    rng.shuffle(homes)
    for i, household in enumerate(households):
        household.home_building_id = homes[i % len(homes)].building_id


def bootstrap_simulation(
    seed: int,
    population: int = 100,
    producer: EventProducer | None = None,
    simulation_id: str = "sim_001",
) -> SimulationEngine:
    world = generate_world(WorldConfig(seed=seed))
    citizens, households = generate_population(seed, n=population)
    businesses = generate_businesses(seed, world, citizens)
    assign_homes(seed, world, households)

    engine = SimulationEngine(world, citizens, households, businesses, producer=producer, simulation_id=simulation_id)
    engine.relationships = generate_relationships(seed, citizens, households, businesses, world)
    return engine
