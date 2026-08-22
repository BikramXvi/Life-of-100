"""Business entities and employment assignment. SRS §6.4, §13.

Businesses are created from the `factory`/`shop` buildings already placed by
`world.generate_world`, and hire from the pool of working-age citizens
produced by `households.generate_population`. At least one food-producing
business (factory) and one food-retail business (shop) are guaranteed so the
drought -> food-price cascade (the submission's showcase scenario) always
has a real chain to travel through.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from life100.simulation.citizens import Citizen
from life100.simulation.world import World

BASE_SALARY = {
    "food_production": 1800.0,
    "manufacturing": 2200.0,
    "food_retail": 1500.0,
    "retail": 1600.0,
}

FACTORY_INDUSTRIES = ("food_production", "manufacturing")
SHOP_INDUSTRIES = ("food_retail", "retail")


@dataclass
class Business:
    business_id: str
    industry: str
    building_id: str
    owner_id: str | None = None
    employee_ids: list[str] = field(default_factory=list)
    cash: float = 0.0
    revenue: float = 0.0
    expenses: float = 0.0
    profit: float = 0.0
    inventory: float = 0.0
    debt: float = 0.0
    price_level: float = 1.0
    active: bool = True

    def headcount(self) -> int:
        return len(self.employee_ids)


def generate_businesses(seed: int, world: World, citizens: list[Citizen]) -> list[Business]:
    """Deterministically create businesses and hire citizens into them.

    Mutates the given citizens' occupation/employer_id/salary in place (this
    runs once, at world-setup time, before the event-driven engine takes
    over — subsequent changes must go through events).
    """
    rng = random.Random(seed)
    businesses: list[Business] = []

    factories = world.buildings_of_kind("factory")
    shops = world.buildings_of_kind("shop")

    unemployed_pool = [c for c in citizens if c.is_working_age() and c.occupation == "unemployed"]
    rng.shuffle(unemployed_pool)

    def next_id(counter: list[int] = [0]) -> str:  # noqa: B006 (intentional single mutable counter)
        counter[0] += 1
        return f"biz_{counter[0]:03d}"

    def hire(business: Business, industry: str) -> None:
        capacity = rng.randint(2, 6)
        base_salary = BASE_SALARY[industry]
        for _ in range(capacity):
            if not unemployed_pool:
                break
            employee = unemployed_pool.pop()
            employee.occupation = industry
            employee.employer_id = business.business_id
            employee.salary = round(base_salary * rng.uniform(0.85, 1.25), 2)
            employee.employment_history.append(f"hired:{business.business_id}")
            business.employee_ids.append(employee.citizen_id)
        if business.employee_ids:
            business.owner_id = business.employee_ids[0]

    for i, building in enumerate(factories):
        industry = FACTORY_INDUSTRIES[0] if i == 0 else rng.choice(FACTORY_INDUSTRIES)
        business = Business(
            business_id=next_id(),
            industry=industry,
            building_id=building.building_id,
            cash=round(rng.uniform(10_000, 60_000), 2),
            inventory=round(rng.uniform(500, 2000), 2),
        )
        hire(business, industry)
        businesses.append(business)

    for i, building in enumerate(shops):
        industry = SHOP_INDUSTRIES[0] if i == 0 else rng.choice(SHOP_INDUSTRIES)
        business = Business(
            business_id=next_id(),
            industry=industry,
            building_id=building.building_id,
            cash=round(rng.uniform(5_000, 30_000), 2),
            inventory=round(rng.uniform(200, 1000), 2),
        )
        hire(business, industry)
        businesses.append(business)

    return businesses
