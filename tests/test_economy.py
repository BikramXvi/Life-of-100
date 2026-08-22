from life100.events.schemas import EventType
from life100.simulation.business import generate_businesses
from life100.simulation.disasters import trigger_drought
from life100.simulation.economy import run_tick
from life100.simulation.engine import SimulationEngine
from life100.simulation.households import generate_population
from life100.simulation.world import WorldConfig, generate_world

SEED = 847291


def _build_engine(n: int = 100) -> SimulationEngine:
    world = generate_world(WorldConfig(seed=SEED))
    citizens, households = generate_population(SEED, n=n)
    businesses = generate_businesses(SEED, world, citizens)
    return SimulationEngine(world, citizens, households, businesses)


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

    for _ in range(15):
        run_tick(engine)

    job_lost_events = engine.log.of_type(EventType.JOB_LOST)
    assert len(job_lost_events) > 0, "expected at least one JOB_LOST event to emerge from the drought"

    # each JOB_LOST event must trace back to a real citizen who is now
    # actually unemployed in engine state (state changed via the event, not
    # directly)
    for event in job_lost_events:
        citizen = engine.citizens[event.source_entity]
        assert citizen.occupation == "unemployed"
        assert citizen.employer_id is None
        assert citizen.salary == 0.0


def test_drought_expires_after_duration():
    engine = _build_engine()
    trigger_drought(engine, duration_ticks=3)
    for _ in range(3):
        run_tick(engine)
    assert "drought" not in engine.active_disasters
    ended_events = engine.log.of_type(EventType.DISASTER_ENDED)
    assert any(e.payload["disaster_type"] == "drought" for e in ended_events)


def test_food_subsidy_policy_dampens_household_expense():
    engine_a = _build_engine()
    engine_b = _build_engine()
    trigger_drought(engine_a)
    trigger_drought(engine_b)
    engine_b.policies["food_subsidy"] = 0.5

    for _ in range(5):
        run_tick(engine_a)
        run_tick(engine_b)

    stress_a = sum(h.financial_stress for h in engine_a.households.values())
    stress_b = sum(h.financial_stress for h in engine_b.households.values())
    assert stress_b <= stress_a
