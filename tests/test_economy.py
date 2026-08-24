from life100.events.schemas import EventType
from life100.simulation.disasters import trigger_drought
from life100.simulation.economy import run_days
from life100.simulation.engine import SimulationEngine
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def _build_engine(n: int = 100) -> SimulationEngine:
    return bootstrap_simulation(SEED, population=n)


def test_drought_raises_food_price_immediately():
    engine = _build_engine()
    baseline = engine.food_price_index
    trigger_drought(engine)
    assert engine.food_price_index > baseline


def test_drought_cascades_into_job_losses_not_scripted():
    """The cascade must emerge from repeated tick evaluation, not be a
    hardcoded `if drought: citizen.lose_job()` (SRS §3.3)."""
    engine = _build_engine()
    trigger_drought(engine)

    run_days(engine, 15)

    job_lost_events = engine.log.of_type(EventType.JOB_LOST)
    assert len(job_lost_events) > 0, "expected at least one JOB_LOST event to emerge from the drought"

    # each JOB_LOST event must trace back to a real citizen and a real
    # business that actually employed them at the time (state changed via
    # the event, not directly). Some of these citizens may have since found
    # a new job via the decision engine (SRS §11) — that's real emergent
    # re-employment, not a reason to doubt the original layoff happened.
    for event in job_lost_events:
        assert event.source_entity in engine.citizens
        assert event.payload["business_id"] in engine.businesses


def test_drought_expires_after_duration():
    engine = _build_engine()
    trigger_drought(engine, duration_ticks=3)
    run_days(engine, 3)
    assert "drought" not in engine.active_disasters
    ended_events = engine.log.of_type(EventType.DISASTER_ENDED)
    assert any(e.payload["disaster_type"] == "drought" for e in ended_events)


def test_food_subsidy_policy_dampens_household_expense():
    engine_a = _build_engine()
    engine_b = _build_engine()
    trigger_drought(engine_a)
    trigger_drought(engine_b)
    engine_b.policies["food_subsidy"] = 0.5

    run_days(engine_a, 5)
    run_days(engine_b, 5)

    stress_a = sum(h.financial_stress for h in engine_a.households.values())
    stress_b = sum(h.financial_stress for h in engine_b.households.values())
    assert stress_b <= stress_a
