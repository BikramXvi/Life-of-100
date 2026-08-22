from life100.simulation.business import generate_businesses
from life100.simulation.households import generate_population
from life100.simulation.world import WorldConfig, generate_world

SEED = 847291


def test_population_size_matches_request():
    citizens, households = generate_population(SEED, n=100)
    assert len(citizens) == 100
    assert sum(h.size() for h in households) == 100


def test_same_seed_produces_identical_population():
    citizens_a, households_a = generate_population(SEED, n=50)
    citizens_b, households_b = generate_population(SEED, n=50)
    assert citizens_a == citizens_b
    assert households_a == households_b


def test_every_citizen_belongs_to_a_household():
    citizens, households = generate_population(SEED, n=50)
    household_ids = {h.household_id for h in households}
    assert all(c.household_id in household_ids for c in citizens)


def test_businesses_hire_working_age_citizens():
    world = generate_world(WorldConfig(seed=SEED))
    citizens, _ = generate_population(SEED, n=100)
    businesses = generate_businesses(SEED, world, citizens)

    assert len(businesses) > 0
    employed = [c for c in citizens if c.employer_id is not None]
    assert len(employed) > 0
    for citizen in employed:
        business = next(b for b in businesses if b.business_id == citizen.employer_id)
        assert citizen.citizen_id in business.employee_ids
        assert citizen.salary > 0

    industries = {b.industry for b in businesses}
    assert "food_production" in industries
    assert "food_retail" in industries
