"""Social relationship graph. SRS §12.

Generated deterministically alongside the rest of the initial population:
family ties from household structure (spouse/parent-child/sibling),
coworker ties from shared employer, neighbor ties from home proximity, and
a handful of friend ties weighted by personality `social_tendency`. Stored
on the engine as `engine.relationships: dict[citizen_id, list[Relationship]]`
— an adjacency list, not a full graph library, which is all this scale
needs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from life100.simulation.business import Business
from life100.simulation.citizens import Citizen
from life100.simulation.households import Household
from life100.simulation.world import World

RELATIONSHIP_TYPES = ("family", "friend", "coworker", "neighbor", "teacher", "employer")
NEIGHBOR_DISTANCE = 2.0


@dataclass
class Relationship:
    citizen_id: str
    other_id: str
    relationship_type: str
    strength: float
    trust: float
    frequency: float  # 0-1, normalized interaction frequency
    history: list[str] = field(default_factory=list)
    last_interaction_tick: int = 0


def _building_coords(world: World) -> dict[str, tuple[int, int]]:
    return {b.building_id: (b.x, b.y) for b in world.buildings}


def generate_relationships(
    seed: int,
    citizens: list[Citizen],
    households: list[Household],
    businesses: list[Business],
    world: World,
) -> dict[str, list[Relationship]]:
    rng = random.Random(seed)
    by_id = {c.citizen_id: c for c in citizens}
    graph: dict[str, list[Relationship]] = {c.citizen_id: [] for c in citizens}

    def add_edge(a_id: str, b_id: str, rel_type: str, strength: float, trust: float, frequency: float) -> None:
        graph[a_id].append(
            Relationship(a_id, b_id, rel_type, strength, trust, frequency, history=[f"formed as {rel_type}"])
        )
        graph[b_id].append(
            Relationship(b_id, a_id, rel_type, strength, trust, frequency, history=[f"formed as {rel_type}"])
        )

    # Family: spouses (each pair recorded once)
    seen_spouse_pairs: set[frozenset[str]] = set()
    for citizen in citizens:
        if citizen.spouse_id:
            pair = frozenset((citizen.citizen_id, citizen.spouse_id))
            if pair not in seen_spouse_pairs:
                seen_spouse_pairs.add(pair)
                add_edge(citizen.citizen_id, citizen.spouse_id, "family", round(rng.uniform(0.85, 0.98), 3),
                          round(rng.uniform(0.85, 0.98), 3), 0.9)
        for child_id in citizen.children_ids:
            add_edge(citizen.citizen_id, child_id, "family", round(rng.uniform(0.8, 0.97), 3),
                      round(rng.uniform(0.8, 0.97), 3), 0.85)

    # Family: siblings (children of the same household)
    for household in households:
        siblings = [cid for cid in household.member_ids if by_id[cid].is_child()]
        for i, a in enumerate(siblings):
            for b in siblings[i + 1:]:
                add_edge(a, b, "family", round(rng.uniform(0.6, 0.9), 3), round(rng.uniform(0.6, 0.9), 3), 0.6)

    # Coworkers: shared employer
    for business in businesses:
        employees = business.employee_ids
        for i, a in enumerate(employees):
            for b in employees[i + 1:]:
                add_edge(a, b, "coworker", round(rng.uniform(0.3, 0.7), 3), round(rng.uniform(0.4, 0.8), 3), 0.5)

    # Neighbors: households whose home buildings are close together
    coords = _building_coords(world)
    for i, hh_a in enumerate(households):
        loc_a = coords.get(hh_a.home_building_id or "")
        if loc_a is None:
            continue
        for hh_b in households[i + 1:]:
            loc_b = coords.get(hh_b.home_building_id or "")
            if loc_b is None:
                continue
            distance = ((loc_a[0] - loc_b[0]) ** 2 + (loc_a[1] - loc_b[1]) ** 2) ** 0.5
            if distance <= NEIGHBOR_DISTANCE:
                adults_a = [cid for cid in hh_a.member_ids if by_id[cid].is_working_age() or by_id[cid].age > 65]
                adults_b = [cid for cid in hh_b.member_ids if by_id[cid].is_working_age() or by_id[cid].age > 65]
                for a in adults_a[:1]:
                    for b in adults_b[:1]:
                        add_edge(a, b, "neighbor", round(rng.uniform(0.2, 0.5), 3), round(rng.uniform(0.3, 0.6), 3), 0.3)

    # Friends: a handful of pairings weighted loosely by social_tendency
    sociable = sorted(
        (c for c in citizens if c.age >= 12), key=lambda c: c.personality.social_tendency, reverse=True
    )
    friend_pool = sociable[: max(2, len(sociable) // 2)]
    rng.shuffle(friend_pool)
    for i in range(0, len(friend_pool) - 1, 2):
        a, b = friend_pool[i], friend_pool[i + 1]
        add_edge(a.citizen_id, b.citizen_id, "friend", round(rng.uniform(0.4, 0.85), 3),
                  round(rng.uniform(0.4, 0.8), 3), round(rng.uniform(0.3, 0.7), 3))

    return graph
