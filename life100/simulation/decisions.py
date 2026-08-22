"""Citizen decision engine. SRS §10 (daily life), §11 (decision system).

Deterministic and seeded — explicitly NOT LLM-driven. SRS §11's AI usage
rule: "Do not use Claude for ordinary low-level decisions. These decisions
should primarily be handled by deterministic simulation logic." Gemini is
reserved for the Government/Historian/Business/Household agents' high-level
reasoning (agents/); this module is the deterministic layer underneath them.

Runs once per tick (called from economy.run_tick) over every living citizen,
using a `random.Random` seeded from (world seed, tick) — reproducible for a
given seed, but distinct draws each tick.
"""

from __future__ import annotations

import random

from life100.events.schemas import EventType
from life100.simulation.engine import SimulationEngine

DAILY_FOOD_COST_PER_ADULT = 12.0
PURCHASE_CHANCE = 0.5
SCHOOL_ATTENDANCE_CHANCE = 0.7
JOB_SEARCH_CHANCE = 0.15
MEDICAL_VISIT_HEALTH_THRESHOLD = 0.55
MEDICAL_VISIT_STRESS_THRESHOLD = 0.75
MEDICAL_VISIT_CHANCE = 0.3
LOAN_DEBT_TRIGGER = -500.0  # savings below this and decent credit -> consider a loan
LOAN_CREDIT_MIN = 550.0
LOAN_CHANCE = 0.4
SOCIAL_INTERACTION_CHANCE = 0.25
MAX_BUSINESS_HEADCOUNT = 8


def run_daily_decisions(engine: SimulationEngine) -> None:
    rng = random.Random(engine.world.seed * 100_003 + engine.tick)

    for citizen in list(engine.citizens.values()):
        if not citizen.alive:
            continue

        if citizen.is_child():
            _decide_school(engine, citizen, rng)
        else:
            _decide_purchase_food(engine, citizen, rng)
            _decide_job_search(engine, citizen, rng)
            _decide_healthcare(engine, citizen, rng)
            _decide_loan(engine, citizen, rng)

        _decide_socialize(engine, citizen, rng)


def _decide_purchase_food(engine: SimulationEngine, citizen, rng: random.Random) -> None:
    if rng.random() > PURCHASE_CHANCE:
        return
    amount = round(DAILY_FOOD_COST_PER_ADULT * engine.food_price_index * rng.uniform(0.8, 1.2), 2)
    engine.emit(
        EventType.PURCHASE,
        source_entity=citizen.citizen_id,
        source_type="citizen",
        payload={"good": "food", "amount": amount},
    )


def _decide_school(engine: SimulationEngine, citizen, rng: random.Random) -> None:
    if rng.random() > SCHOOL_ATTENDANCE_CHANCE:
        return
    engine.emit(
        EventType.SCHOOL_ATTENDED,
        source_entity=citizen.citizen_id,
        source_type="citizen",
        payload={"education_level": citizen.education_level},
    )


def _decide_job_search(engine: SimulationEngine, citizen, rng: random.Random) -> None:
    if citizen.occupation != "unemployed" or rng.random() > JOB_SEARCH_CHANCE:
        return
    candidates = [
        b
        for b in engine.businesses.values()
        if b.active and b.headcount() < MAX_BUSINESS_HEADCOUNT
    ]
    if not candidates:
        return
    business = min(candidates, key=lambda b: (b.headcount(), b.business_id))
    from life100.simulation.business import BASE_SALARY

    base_salary = BASE_SALARY.get(business.industry, 1500.0)
    salary = round(base_salary * rng.uniform(0.85, 1.15), 2)
    engine.emit(
        EventType.JOB_STARTED,
        source_entity=citizen.citizen_id,
        source_type="citizen",
        payload={"business_id": business.business_id, "occupation": business.industry, "salary": salary},
    )


def _decide_healthcare(engine: SimulationEngine, citizen, rng: random.Random) -> None:
    needs_care = citizen.health_score < MEDICAL_VISIT_HEALTH_THRESHOLD or citizen.stress > MEDICAL_VISIT_STRESS_THRESHOLD
    # government.healthcare_spending is a real lever, not decorative: better
    # funding means better access (higher chance someone who needs care
    # actually gets it) and lower out-of-pocket cost (subsidized), not just
    # a number sitting in the Government dataclass.
    funding = engine.government.healthcare_spending
    access_chance = min(1.0, MEDICAL_VISIT_CHANCE * (1.0 + funding))
    if not needs_care or rng.random() > access_chance:
        return
    cost = round(rng.uniform(20, 150) * max(0.1, 1.0 - funding), 2)
    reason = "stress-related checkup" if citizen.stress > MEDICAL_VISIT_STRESS_THRESHOLD else "general checkup"
    engine.emit(
        EventType.MEDICAL_VISIT,
        source_entity=citizen.citizen_id,
        source_type="citizen",
        payload={"cost": cost, "reason": reason},
    )


def _decide_loan(engine: SimulationEngine, citizen, rng: random.Random) -> None:
    needs_loan = citizen.savings < LOAN_DEBT_TRIGGER and citizen.credit_score >= LOAN_CREDIT_MIN
    if not needs_loan or rng.random() > LOAN_CHANCE:
        return
    amount = round(rng.uniform(200, 1000), 2)
    engine.emit(
        EventType.LOAN_CREATED,
        source_entity=citizen.citizen_id,
        source_type="citizen",
        payload={"amount": amount, "interest_rate": engine.government.interest_rate},
    )


def _decide_socialize(engine: SimulationEngine, citizen, rng: random.Random) -> None:
    edges = engine.relationships.get(citizen.citizen_id, [])
    if not edges or rng.random() > SOCIAL_INTERACTION_CHANCE * citizen.personality.social_tendency:
        return
    edge = rng.choice(edges)
    engine.emit(
        EventType.RELATIONSHIP_CHANGED,
        source_entity=citizen.citizen_id,
        source_type="citizen",
        payload={
            "citizen_id": citizen.citizen_id,
            "other_id": edge.other_id,
            "relationship_type": edge.relationship_type,
            "strength_delta": round(rng.uniform(0.01, 0.05), 3),
        },
    )
