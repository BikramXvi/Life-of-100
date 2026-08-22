from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def test_relationships_are_generated_for_every_citizen():
    engine = bootstrap_simulation(SEED, population=100)
    assert set(engine.relationships.keys()) == set(engine.citizens.keys())


def test_married_couples_have_a_family_relationship_edge():
    engine = bootstrap_simulation(SEED, population=100)
    married = [c for c in engine.citizens.values() if c.is_married()]
    assert married
    citizen = married[0]
    edges = engine.relationships[citizen.citizen_id]
    assert any(r.other_id == citizen.spouse_id and r.relationship_type == "family" for r in edges)


def test_coworkers_have_a_coworker_relationship_edge():
    engine = bootstrap_simulation(SEED, population=100)
    business = next(b for b in engine.businesses.values() if b.headcount() >= 2)
    a, b = business.employee_ids[0], business.employee_ids[1]
    edges = engine.relationships[a]
    assert any(r.other_id == b and r.relationship_type == "coworker" for r in edges)


def test_households_are_assigned_a_home_building():
    engine = bootstrap_simulation(SEED, population=50)
    assert all(h.home_building_id is not None for h in engine.households.values())
    home_ids = {b.building_id for b in engine.world.buildings_of_kind("home")}
    assert all(h.home_building_id in home_ids for h in engine.households.values())


def test_relationships_are_deterministic():
    engine_a = bootstrap_simulation(SEED, population=40)
    engine_b = bootstrap_simulation(SEED, population=40)
    for citizen_id in engine_a.relationships:
        edges_a = [(r.other_id, r.relationship_type) for r in engine_a.relationships[citizen_id]]
        edges_b = [(r.other_id, r.relationship_type) for r in engine_b.relationships[citizen_id]]
        assert edges_a == edges_b
