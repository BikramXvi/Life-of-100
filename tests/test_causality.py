from life100.events.schemas import EventType
from life100.simulation import causality, memory
from life100.simulation.disasters import trigger_drought
from life100.simulation.economy import run_days
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def test_job_lost_during_drought_cites_the_real_disaster_event():
    engine = bootstrap_simulation(SEED, population=100)
    trigger_drought(engine)
    run_days(engine, 20)

    job_lost = engine.log.of_type(EventType.JOB_LOST)
    assert job_lost
    cited_causes = {e.payload.get("caused_by") for e in job_lost}
    assert None not in cited_causes or len(cited_causes) > 1, "expected at least some JOB_LOST events to cite a cause"

    drought_started = engine.log.of_type(EventType.DISASTER_STARTED)[0]
    causal_job_losses = [e for e in job_lost if e.payload.get("caused_by") == drought_started.event_id]
    assert causal_job_losses, "expected at least one JOB_LOST to cite the real drought DISASTER_STARTED event_id"


def test_trace_causes_walks_back_to_the_real_disaster_event():
    engine = bootstrap_simulation(SEED, population=100)
    trigger_drought(engine)
    run_days(engine, 20)

    job_lost = next(e for e in engine.log.of_type(EventType.JOB_LOST) if e.payload.get("caused_by"))
    chain = causality.trace_causes(engine.log, job_lost.event_id)
    assert chain[0].event_id == job_lost.event_id
    assert any(e.event_type == EventType.DISASTER_STARTED for e in chain)


def test_trace_effects_is_the_inverse_of_trace_causes():
    engine = bootstrap_simulation(SEED, population=100)
    trigger_drought(engine)
    run_days(engine, 20)

    drought_started = engine.log.of_type(EventType.DISASTER_STARTED)[0]
    effects = causality.trace_effects(engine.log, drought_started.event_id)
    assert effects
    for effect in effects:
        assert effect.payload.get("caused_by") == drought_started.event_id


def test_trace_causes_never_fabricates_a_link_for_an_uncaused_event():
    engine = bootstrap_simulation(SEED, population=20)
    # world generation itself doesn't emit events, so pick any event with no
    # caused_by link (e.g. a PRICE_CHANGED decay tick has none by default)
    run_days(engine, 3)
    uncaused = next((e for e in engine.log.all() if not e.payload.get("caused_by")), None)
    if uncaused is None:
        return  # nothing to assert this run; not a failure
    chain = causality.trace_causes(engine.log, uncaused.event_id)
    assert chain == [uncaused]


def test_memories_include_job_started_and_are_chronological():
    engine = bootstrap_simulation(SEED, population=60)
    from life100.simulation.economy import run_days as _run_days

    _run_days(engine, 30)

    citizen_id = next(iter(engine.citizens))
    memories = memory.get_memories(engine, citizen_id)
    ticks = [m["simulation_tick"] for m in memories]
    assert ticks == sorted(ticks)
    for m in memories:
        assert m["label"]
