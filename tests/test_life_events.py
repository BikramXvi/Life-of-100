from life100.events.schemas import EventType
from life100.simulation.economy import run_tick
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def _run(n=100, ticks=200):
    engine = bootstrap_simulation(SEED, population=n)
    for _ in range(ticks):
        run_tick(engine)
    return engine


def test_marriages_link_spouses_and_merge_households():
    engine = _run()
    marriages = engine.log.of_type(EventType.MARRIAGE)
    assert marriages, "expected at least one marriage over a 200-tick run of 100 citizens"
    event = marriages[0]
    a = engine.citizens[event.payload["citizen_id"]]
    b = engine.citizens[event.payload["spouse_id"]]
    assert a.spouse_id == b.citizen_id
    assert b.spouse_id == a.citizen_id
    assert a.marital_status == b.marital_status == "married"
    assert a.household_id == b.household_id


def test_deaths_mark_citizen_not_alive_and_free_their_job():
    engine = _run()
    deaths = engine.log.of_type(EventType.CITIZEN_DIED)
    assert deaths, "expected at least one death over a 200-tick run"
    for event in deaths:
        citizen = engine.citizens[event.source_entity]
        assert citizen.alive is False
        assert citizen.employer_id is None
        for business in engine.businesses.values():
            assert citizen.citizen_id not in business.employee_ids


def test_child_born_creates_a_real_new_citizen_with_family_ties():
    engine = _run()
    births = engine.log.of_type(EventType.CHILD_BORN)
    assert births, "expected at least one birth over a 200-tick run"
    event = births[0]
    child = engine.citizens.get(event.payload["citizen_id"])
    assert child is not None
    assert child.age == 0
    for parent_id in event.payload["parent_ids"]:
        assert child.citizen_id in engine.citizens[parent_id].children_ids
        assert parent_id in child.parent_ids
        edges = engine.relationships[child.citizen_id]
        assert any(r.other_id == parent_id and r.relationship_type == "family" for r in edges)
    household = engine.households[child.household_id]
    assert child.citizen_id in household.member_ids


def test_life_events_are_deterministic():
    engine_a = _run(n=80, ticks=100)
    engine_b = _run(n=80, ticks=100)
    types_a = [(e.event_type, e.source_entity, e.simulation_tick) for e in engine_a.log.all()]
    types_b = [(e.event_type, e.source_entity, e.simulation_tick) for e in engine_b.log.all()]
    assert types_a == types_b
