"""Life-course events. SRS §6.3 (family events), part of §10/§11's daily
cycle. Deterministic and seeded, same as decisions.py — aging, death,
marriage, divorce, and childbirth are demographic facts, not AI decisions.

Probabilities are tuned low per tick (these are meant to be occasional life
events over a population, not everyday occurrences) but population-wide, so
a multi-week run does show some.
"""

from __future__ import annotations

import random

from life100.events.schemas import EventType
from life100.simulation.citizens import FIRST_NAMES, LAST_NAMES
from life100.simulation.engine import SimulationEngine

DAYS_PER_YEAR = 365
DEATH_AGE_THRESHOLD = 60  # initial adults are generated up to age 65 (households.py),
# so this must sit below that or nobody is ever at risk within a short demo run
# (aging only advances once per simulated year, DAYS_PER_YEAR ticks)
DEATH_BASE_CHANCE_PER_TICK = 0.0006  # scaled up by age past the threshold and poor health
MARRIAGE_MIN_AGE = 20
MARRIAGE_CHANCE_PER_TICK = 0.01
DIVORCE_STRENGTH_THRESHOLD = 0.35
DIVORCE_CHANCE_PER_TICK = 0.003
CHILDBEARING_AGE_RANGE = (20, 42)
MAX_CHILDREN_PER_COUPLE = 3
CHILD_BORN_CHANCE_PER_TICK = 0.01


def run_tick_life_events(engine: SimulationEngine) -> None:
    rng = random.Random(engine.world.seed * 7_919 + engine.tick)
    _age_population(engine)
    _consider_deaths(engine, rng)
    _consider_marriages(engine, rng)
    _consider_divorces(engine, rng)
    _consider_births(engine, rng)


def _age_population(engine: SimulationEngine) -> None:
    if engine.tick > 0 and engine.tick % DAYS_PER_YEAR == 0:
        for citizen in engine.citizens.values():
            if citizen.alive:
                citizen.age += 1


def _consider_deaths(engine: SimulationEngine, rng: random.Random) -> None:
    for citizen in list(engine.citizens.values()):
        if not citizen.alive or citizen.age < DEATH_AGE_THRESHOLD:
            continue
        age_factor = (citizen.age - DEATH_AGE_THRESHOLD + 1) * 0.15
        health_factor = 1.0 + (1.0 - citizen.health_score)
        chance = DEATH_BASE_CHANCE_PER_TICK * age_factor * health_factor
        if rng.random() < chance:
            # Record family ties as they stood at the moment of death — the
            # event is the immutable historical fact; engine.py's handler
            # clears the surviving spouse's live spouse_id afterward, so
            # relying on later state here would lose the connection
            # (simulation/memory.py depends on this snapshot).
            engine.emit(
                EventType.CITIZEN_DIED,
                source_entity=citizen.citizen_id,
                source_type="citizen",
                payload={
                    "age": citizen.age,
                    "cause": "natural causes",
                    "spouse_id": citizen.spouse_id,
                    "parent_ids": list(citizen.parent_ids),
                    "children_ids": list(citizen.children_ids),
                },
            )


def _consider_marriages(engine: SimulationEngine, rng: random.Random) -> None:
    eligible = [
        c
        for c in engine.citizens.values()
        if c.alive and c.marital_status == "single" and c.age >= MARRIAGE_MIN_AGE
    ]
    if len(eligible) < 2:
        return
    eligible.sort(key=lambda c: c.citizen_id)  # deterministic order before shuffling
    rng.shuffle(eligible)
    paired: set[str] = set()
    for citizen in eligible:
        if citizen.citizen_id in paired or rng.random() > MARRIAGE_CHANCE_PER_TICK:
            continue
        candidates = [
            c
            for c in eligible
            if c.citizen_id != citizen.citizen_id
            and c.citizen_id not in paired
            and c.gender != citizen.gender
            and abs(c.age - citizen.age) <= 15
        ]
        if not candidates:
            continue
        partner = rng.choice(candidates)
        paired.add(citizen.citizen_id)
        paired.add(partner.citizen_id)
        engine.emit(
            EventType.MARRIAGE,
            source_entity=citizen.citizen_id,
            source_type="citizen",
            payload={"citizen_id": citizen.citizen_id, "spouse_id": partner.citizen_id},
        )


def _consider_divorces(engine: SimulationEngine, rng: random.Random) -> None:
    seen: set[str] = set()
    for citizen in list(engine.citizens.values()):
        if (
            not citizen.alive
            or citizen.marital_status != "married"
            or citizen.spouse_id is None
            or citizen.citizen_id in seen
        ):
            continue
        seen.add(citizen.citizen_id)
        seen.add(citizen.spouse_id)

        edges = engine.relationships.get(citizen.citizen_id, [])
        family_edge = next((r for r in edges if r.other_id == citizen.spouse_id), None)
        strength = family_edge.strength if family_edge else 0.9
        if strength < DIVORCE_STRENGTH_THRESHOLD and rng.random() < DIVORCE_CHANCE_PER_TICK:
            engine.emit(
                EventType.DIVORCE,
                source_entity=citizen.citizen_id,
                source_type="citizen",
                payload={"citizen_id": citizen.citizen_id, "spouse_id": citizen.spouse_id},
            )


def _consider_births(engine: SimulationEngine, rng: random.Random) -> None:
    seen: set[str] = set()
    citizen_seq = len(engine.citizens) + 1
    for citizen in list(engine.citizens.values()):
        if (
            not citizen.alive
            or citizen.gender != "female"
            or citizen.marital_status != "married"
            or citizen.spouse_id is None
            or citizen.citizen_id in seen
            or not (CHILDBEARING_AGE_RANGE[0] <= citizen.age <= CHILDBEARING_AGE_RANGE[1])
        ):
            continue
        seen.add(citizen.citizen_id)
        if len(citizen.children_ids) >= MAX_CHILDREN_PER_COUPLE:
            continue
        if rng.random() > CHILD_BORN_CHANCE_PER_TICK:
            continue

        child_id = f"cit_{citizen_seq:04d}_b{engine.tick}"
        citizen_seq += 1
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        gender = rng.choice(("female", "male"))
        engine.emit(
            EventType.CHILD_BORN,
            source_entity=child_id,
            source_type="citizen",
            payload={
                "citizen_id": child_id,
                "name": name,
                "gender": gender,
                "household_id": citizen.household_id,
                "parent_ids": [citizen.citizen_id, citizen.spouse_id],
            },
        )
