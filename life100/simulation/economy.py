"""Per-tick economic update loop. SRS §13.

This is the simplified stand-in for SRS §10's full tick-by-tick daily
routines (see SCOPE.md) — instead of simulating every citizen's day, each
tick recomputes food prices, business finances, and household budgets, which
is enough to produce a genuine, non-scripted cascade:

    drought -> food price up -> food-business costs up -> business profit
    down -> business revenue-side demand down economy-wide (households under
    stress spend less everywhere) -> layoffs -> citizen income/savings down
    -> citizen stress up

Nothing here mutates state directly — every effect is an `engine.emit(...)`
call; the engine's handlers (engine.py) are what actually change a Citizen/
Household/Business.
"""

from __future__ import annotations

from life100.events.schemas import EventType
from life100.simulation import decisions, life_events
from life100.simulation.engine import SimulationEngine
from life100.simulation.resources import (
    DROUGHT_PRODUCTION_MULTIPLIER,
    FOOD_CONSUMPTION_PER_CAPITA,
    FOOD_YIELD_PER_WORKER,
    RAW_MATERIAL_USE_PER_WORKER,
)

FOOD_INDUSTRIES = ("food_production", "food_retail")
BASE_REVENUE_PER_EMPLOYEE = 300.0
BASE_COST_PER_EMPLOYEE = 100.0
BASE_HOUSEHOLD_COST_PER_MEMBER = 40.0

# `Citizen.salary`/`BASE_SALARY` (business.py) are monthly figures (matches
# the SRS's own NPR-salary examples) but one tick = one simulated day
# (SCOPE.md). Dividing by this converts salary into the daily flow the
# per-tick business/household budget arithmetic below actually needs —
# without it every business is insolvent from tick 1 regardless of the
# economy, since a month's salary would be charged as a single day's cost.
SALARY_PERIOD_DAYS = 30


def run_tick(engine: SimulationEngine) -> None:
    engine.tick += 1
    _expire_disasters(engine)
    _update_food_price(engine)
    _update_businesses(engine)
    _update_households(engine)
    _update_resources(engine)
    decisions.run_daily_decisions(engine)
    life_events.run_tick_life_events(engine)


def _expire_disasters(engine: SimulationEngine) -> None:
    expired = [
        name
        for name, info in engine.active_disasters.items()
        if engine.tick - info["started_tick"] >= info["duration"]
    ]
    for name in expired:
        engine.emit(
            EventType.DISASTER_ENDED,
            source_entity=name,
            source_type="disaster",
            payload={"disaster_type": name},
        )


def _update_food_price(engine: SimulationEngine) -> None:
    if "drought" in engine.active_disasters:
        new_index = min(engine.food_price_index * 1.08, 3.0)
    else:
        new_index = max(1.0, engine.food_price_index * 0.97)
    if abs(new_index - engine.food_price_index) > 1e-6:
        engine.emit(
            EventType.PRICE_CHANGED,
            source_entity="market_food",
            source_type="business",
            payload={
                "good": "food",
                "old_index": round(engine.food_price_index, 4),
                "new_index": round(new_index, 4),
            },
        )


def _average_household_stress(engine: SimulationEngine) -> float:
    households = list(engine.households.values())
    if not households:
        return 0.0
    return sum(h.financial_stress for h in households) / len(households)


def _update_businesses(engine: SimulationEngine) -> None:
    broad_cost_multiplier, broad_demand_multiplier = engine.broad_disaster_multipliers()
    demand_multiplier = max(0.5, 1.0 - _average_household_stress(engine) * 0.6) * broad_demand_multiplier
    for business in list(engine.businesses.values()):
        if not business.active:
            continue
        headcount = business.headcount()
        food_cost_multiplier = engine.food_price_index if business.industry in FOOD_INDUSTRIES else 1.0
        cost_multiplier = food_cost_multiplier * broad_cost_multiplier

        daily_salaries = (
            sum(engine.citizens[cid].salary for cid in business.employee_ids if cid in engine.citizens)
            / SALARY_PERIOD_DAYS
        )
        business.revenue = round(headcount * BASE_REVENUE_PER_EMPLOYEE * demand_multiplier, 2)
        business.expenses = round(daily_salaries + headcount * BASE_COST_PER_EMPLOYEE * cost_multiplier, 2)
        business.profit = round(business.revenue - business.expenses, 2)
        business.cash = round(business.cash + business.profit, 2)

        if business.cash < 0 and business.employee_ids:
            # Shed the most recently hired employee first (shortest
            # employment history) — deterministic, no RNG needed.
            employee_id = min(
                business.employee_ids,
                key=lambda cid: len(engine.citizens[cid].employment_history),
            )
            engine.emit(
                EventType.JOB_LOST,
                source_entity=employee_id,
                source_type="citizen",
                payload={"business_id": business.business_id, "reason": "business_cost_pressure"},
            )
            business.cash = max(business.cash, 0.0)

        if business.cash <= 0 and not business.employee_ids:
            engine.emit(
                EventType.BUSINESS_FAILED,
                source_entity=business.business_id,
                source_type="business",
                payload={"reason": "insolvent"},
            )


def _update_households(engine: SimulationEngine) -> None:
    subsidy = engine.policies.get("food_subsidy", 0.0)
    for household in engine.households.values():
        members = [engine.citizens[cid] for cid in household.member_ids if cid in engine.citizens]
        if not members:
            continue
        income = sum(m.salary for m in members) / SALARY_PERIOD_DAYS
        effective_price = max(engine.food_price_index - subsidy, 0.3)
        expenses = round(BASE_HOUSEHOLD_COST_PER_MEMBER * len(members) * effective_price, 2)

        household.income = round(income, 2)
        household.expenses = expenses
        net = income - expenses
        household.savings = round(household.savings + net, 2)

        if net < 0:
            household.debt = round(household.debt + (-net) * 0.5, 2)
            household.financial_stress = round(min(1.0, household.financial_stress + 0.05), 3)
            for member in members:
                member.stress = round(min(1.0, member.stress + 0.03), 3)
        else:
            household.financial_stress = round(max(0.0, household.financial_stress - 0.02), 3)


def _update_resources(engine: SimulationEngine) -> None:
    """Tracks SRS §6.7 resource stocks alongside the price mechanism above
    (additive, doesn't change food_price_index itself — see resources.py)."""
    food_producers = [b for b in engine.businesses.values() if b.active and b.industry == "food_production"]
    manufacturers = [b for b in engine.businesses.values() if b.active and b.industry == "manufacturing"]

    yield_multiplier = DROUGHT_PRODUCTION_MULTIPLIER if "drought" in engine.active_disasters else 1.0
    production = sum(b.headcount() for b in food_producers) * FOOD_YIELD_PER_WORKER * yield_multiplier
    consumption = len(engine.citizens) * FOOD_CONSUMPTION_PER_CAPITA
    engine.resources.food_stock = max(0.0, round(engine.resources.food_stock - consumption + production, 2))

    raw_material_use = sum(b.headcount() for b in manufacturers) * RAW_MATERIAL_USE_PER_WORKER
    if raw_material_use > 0:
        engine.resources.raw_materials_stock = max(0.0, round(engine.resources.raw_materials_stock - raw_material_use, 2))
        engine.emit(
            EventType.RESOURCE_EXTRACTED,
            source_entity="resources",
            source_type="environment",
            payload={
                "resource": "raw_materials",
                "amount": raw_material_use,
                "remaining": engine.resources.raw_materials_stock,
            },
        )
