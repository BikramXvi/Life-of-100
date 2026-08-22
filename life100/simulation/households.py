"""Household/family structures and population generation. SRS §6.2, §6.3.

`generate_population` is the single deterministic entry point that produces
a coherent set of citizens *and* the households/families they belong to —
ages, marital/parent-child ties, and household composition are generated
together so they stay consistent (e.g. children are never older than their
parents, and a "couple" household's two adults are recorded as married to
each other).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from life100.simulation.citizens import (
    CAREER_GOALS,
    FAMILY_GOALS,
    FINANCIAL_GOALS,
    FIRST_NAMES,
    LAST_NAMES,
    PERSONAL_GOALS,
    Citizen,
    Goals,
    Personality,
)

HOUSEHOLD_COMPOSITIONS = ("single_adult", "couple", "couple_with_children", "single_parent")
HOUSEHOLD_WEIGHTS = (0.20, 0.30, 0.35, 0.15)
LIVING_CONDITIONS = ("modest", "comfortable", "cramped", "spacious")


@dataclass
class Household:
    household_id: str
    member_ids: list[str] = field(default_factory=list)
    home_building_id: str | None = None
    property_value: float = 0.0
    income: float = 0.0
    expenses: float = 0.0
    savings: float = 0.0
    debt: float = 0.0
    assets: float = 0.0
    goals: list[str] = field(default_factory=list)
    financial_stress: float = 0.0
    living_conditions: str = "modest"

    def size(self) -> int:
        return len(self.member_ids)


def _make_personality(rng: random.Random) -> Personality:
    return Personality(
        risk_tolerance=round(rng.random(), 3),
        ambition=round(rng.random(), 3),
        patience=round(rng.random(), 3),
        social_tendency=round(rng.random(), 3),
    )


def _make_goals(rng: random.Random) -> Goals:
    return Goals(
        career_goal=rng.choice(CAREER_GOALS),
        financial_goal=rng.choice(FINANCIAL_GOALS),
        family_goal=rng.choice(FAMILY_GOALS),
        personal_goal=rng.choice(PERSONAL_GOALS),
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
        assets=round(rng.uniform(0, 20_000), 2) if age >= 18 else 0.0,
        credit_score=round(rng.uniform(500, 800), 1) if age >= 18 else 0.0,
        health_score=round(rng.uniform(0.6, 0.95), 3),
        fitness=round(rng.uniform(0.4, 0.9), 3),
        stress=round(rng.uniform(0.1, 0.4), 3),
        sleep=round(rng.uniform(0.5, 0.9), 3),
        spending_habit=round(rng.random(), 3),
        leisure_activity=rng.choice(("recreation", "sports", "reading", "socializing", "arts")),
        goals=_make_goals(rng) if age >= 15 else None,
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
        adults: list[Citizen] = []
        children: list[Citizen] = []

        def add_adult() -> Citizen:
            nonlocal citizen_seq
            citizen_seq += 1
            citizen = _make_citizen(rng, f"cit_{citizen_seq:04d}", rng.randint(20, 65))
            members.append(citizen)
            adults.append(citizen)
            return citizen

        def add_child() -> Citizen:
            nonlocal citizen_seq
            citizen_seq += 1
            citizen = _make_citizen(rng, f"cit_{citizen_seq:04d}", rng.randint(0, 17))
            members.append(citizen)
            children.append(citizen)
            return citizen

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
            adults = [c for c in adults if c in members]
            children = [c for c in children if c in members]

        # Family ties (SRS §6.3): a 2-adult household is a married couple;
        # every adult present is recorded as a parent of every child present.
        if len(adults) == 2:
            a, b = adults
            a.spouse_id, b.spouse_id = b.citizen_id, a.citizen_id
            a.marital_status = b.marital_status = "married"
        for parent in adults:
            for child in children:
                parent.children_ids.append(child.citizen_id)
                child.parent_ids.append(parent.citizen_id)

        for member in members:
            member.household_id = household_id

        citizens.extend(members)
        households.append(
            Household(
                household_id=household_id,
                member_ids=[m.citizen_id for m in members],
                property_value=round(rng.uniform(20_000, 150_000), 2),
                assets=round(sum(m.assets for m in members), 2),
                goals=[rng.choice(FINANCIAL_GOALS), rng.choice(FAMILY_GOALS)],
                living_conditions=rng.choice(LIVING_CONDITIONS),
            )
        )
        remaining -= len(members)

    return citizens, households
