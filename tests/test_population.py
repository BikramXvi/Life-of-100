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


def test_couples_are_recorded_as_married_to_each_other():
    citizens, _ = generate_population(SEED, n=100)
    by_id = {c.citizen_id: c for c in citizens}
    married = [c for c in citizens if c.marital_status == "married"]
    assert married, "expected at least one married couple in a 100-citizen population"
    for citizen in married:
        spouse = by_id[citizen.spouse_id]
        assert spouse.spouse_id == citizen.citizen_id
        assert spouse.marital_status == "married"


def test_parent_child_ties_are_reciprocal():
    citizens, _ = generate_population(SEED, n=100)
    by_id = {c.citizen_id: c for c in citizens}
    children_with_parents = [c for c in citizens if c.parent_ids]
    assert children_with_parents
    for child in children_with_parents:
        for parent_id in child.parent_ids:
            assert child.citizen_id in by_id[parent_id].children_ids


def test_adults_have_goals():
    citizens, _ = generate_population(SEED, n=50)
    adults = [c for c in citizens if c.age >= 18]
    assert all(c.goals is not None for c in adults)
