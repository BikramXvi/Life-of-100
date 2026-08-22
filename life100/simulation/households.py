"""Household/family structures and population generation. SRS §6.2, §6.3.

`generate_population` is the single deterministic entry point that produces
a coherent set of citizens *and* the households/families they belong to —
ages and relationships are generated together so they stay consistent (e.g.
children are never older than their parents).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from life100.simulation.citizens import (
    FIRST_NAMES,
    LAST_NAMES,
    Citizen,
    Personality,
)

HOUSEHOLD_COMPOSITIONS = ("single_adult", "couple", "couple_with_children", "single_parent")
HOUSEHOLD_WEIGHTS = (0.20, 0.30, 0.35, 0.15)


@dataclass
class Household:
    household_id: str
    member_ids: list[str] = field(default_factory=list)
    home_building_id: str | None = None
    income: float = 0.0
    expenses: float = 0.0
    savings: float = 0.0
    debt: float = 0.0
    financial_stress: float = 0.0

    def size(self) -> int:
        return len(self.member_ids)


def _make_personality(rng: random.Random) -> Personality:
    return Personality(
        risk_tolerance=round(rng.random(), 3),
        ambition=round(rng.random(), 3),
        patience=round(rng.random(), 3),
        social_tendency=round(rng.random(), 3),
    )


def _make_citizen(rng: random.Random, citizen_id: str, age: int) -> Citizen:
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    gender = rng.choice(("female", "male"))
    occupation = "student" if age < 18 else "unemployed"
    education_level = "none"
    if age >= 18:
        education_level = rng.choice(("secondary", "secondary", "university"))
    return Citizen(
        citizen_id=citizen_id,
        name=name,
        age=age,
        gender=gender,
        personality=_make_personality(rng),
        occupation=occupation,
        education_level=education_level,
        savings=round(rng.uniform(0, 50_000), 2) if age >= 18 else 0.0,
        health_score=round(rng.uniform(0.6, 0.95), 3),
        stress=round(rng.uniform(0.1, 0.4), 3),
    )


def generate_population(seed: int, n: int = 100) -> tuple[list[Citizen], list[Household]]:
    """Deterministically generate ~n citizens grouped into coherent households.

    Same seed + n -> identical citizens and households.
    """
    rng = random.Random(seed)
    citizens: list[Citizen] = []
    households: list[Household] = []

    citizen_seq = 0
    household_seq = 0
    remaining = n

    while remaining > 0:
        household_seq += 1
        household_id = f"hh_{household_seq:03d}"
        composition = rng.choices(HOUSEHOLD_COMPOSITIONS, weights=HOUSEHOLD_WEIGHTS)[0]

        members: list[Citizen] = []

        def add_adult() -> None:
            nonlocal citizen_seq
            citizen_seq += 1
            members.append(_make_citizen(rng, f"cit_{citizen_seq:04d}", rng.randint(20, 65)))

        def add_child() -> None:
            nonlocal citizen_seq
            citizen_seq += 1
            members.append(_make_citizen(rng, f"cit_{citizen_seq:04d}", rng.randint(0, 17)))

        if composition == "single_adult":
            add_adult()
        elif composition == "couple":
            add_adult()
            add_adult()
        elif composition == "couple_with_children":
            add_adult()
            add_adult()
            for _ in range(rng.randint(1, 3)):
                add_child()
        elif composition == "single_parent":
            add_adult()
            for _ in range(rng.randint(1, 2)):
                add_child()

        if len(members) > remaining:
            members = members[:remaining]

        for member in members:
            member.household_id = household_id

        citizens.extend(members)
        households.append(Household(household_id=household_id, member_ids=[m.citizen_id for m in members]))
        remaining -= len(members)

    return citizens, households
