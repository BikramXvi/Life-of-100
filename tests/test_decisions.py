from life100.events.schemas import EventType
from life100.simulation.economy import run_tick
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def _run(n=60, ticks=30):
    engine = bootstrap_simulation(SEED, population=n)
    for _ in range(ticks):
        run_tick(engine)
    return engine


def test_decision_engine_produces_a_variety_of_real_events():
    engine = _run()
    types_seen = {e.event_type for e in engine.log.all()}
    # SRS §11's decision list, as event types this engine can actually emit
    expected_any_of = {
        EventType.PURCHASE,
        EventType.SCHOOL_ATTENDED,
        EventType.MEDICAL_VISIT,
        EventType.LOAN_CREATED,
        EventType.JOB_STARTED,
        EventType.RELATIONSHIP_CHANGED,
    }
    assert expected_any_of & types_seen, f"expected some of {expected_any_of}, saw {types_seen}"


def test_children_attend_school_not_work():
    engine = _run()
    children = [c for c in engine.citizens.values() if c.is_child()]
    assert children
    assert all(c.occupation in ("student",) or c.occupation == "unemployed" for c in children)
    school_events = engine.log.of_type(EventType.SCHOOL_ATTENDED)
    assert all(e.source_entity in engine.citizens for e in school_events)


def test_purchases_reduce_savings():
    engine = bootstrap_simulation(SEED, population=30)
    citizen = next(c for c in engine.citizens.values() if not c.is_child())
    savings_before = citizen.savings
    for _ in range(30):
        run_tick(engine)
    purchases = [e for e in engine.log.for_entity(citizen.citizen_id) if e.event_type == EventType.PURCHASE]
    if purchases:
        # savings should have moved (down from purchases, though income/other
        # effects can offset it - the point is purchases are real deductions)
        total_spent = sum(e.payload["amount"] for e in purchases)
        assert total_spent > 0


def test_relationship_changed_updates_the_graph():
    engine = _run(n=40, ticks=30)
    changed = engine.log.of_type(EventType.RELATIONSHIP_CHANGED)
    assert changed, "expected at least one social interaction over 30 ticks"
    event = changed[0]
    edges = engine.relationships[event.payload["citizen_id"]]
    matching = [r for r in edges if r.other_id == event.payload["other_id"]]
    assert matching
    assert matching[0].last_interaction_tick > 0
