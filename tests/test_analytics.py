from life100.api.routers.analytics import compute_metrics_timeseries
from life100.simulation.disasters import trigger_drought
from life100.simulation.economy import run_tick
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def test_metrics_timeseries_reconstructs_correctly_and_matches_current_state():
    engine = bootstrap_simulation(SEED, population=100)
    trigger_drought(engine)
    for _ in range(30):
        run_tick(engine)

    series = compute_metrics_timeseries(engine)

    assert len(series) == engine.tick + 1
    assert series[0]["tick"] == 0
    assert series[-1]["tick"] == engine.tick

    # the reconstructed final point must exactly match the engine's real
    # current state -- that's the anchor the whole backward walk depends on
    current_population = sum(1 for c in engine.citizens.values() if c.alive)
    current_employed = sum(
        1
        for c in engine.citizens.values()
        if c.is_working_age() and c.occupation not in ("unemployed", "deceased")
    )
    current_active_businesses = sum(1 for b in engine.businesses.values() if b.active)

    assert series[-1]["population"] == current_population
    assert series[-1]["employed"] == current_employed
    assert series[-1]["active_businesses"] == current_active_businesses
    assert series[-1]["food_price_index"] == round(engine.food_price_index, 4)


def test_metrics_timeseries_food_price_reflects_the_drought_shock():
    engine = bootstrap_simulation(SEED, population=50)
    trigger_drought(engine)
    for _ in range(10):
        run_tick(engine)

    series = compute_metrics_timeseries(engine)
    prices = [row["food_price_index"] for row in series]
    assert prices[0] > 1.0, "the drought's immediate shock must appear from tick 0 onward"
    assert max(prices) >= prices[0]


def test_metrics_timeseries_with_no_events_is_flat():
    engine = bootstrap_simulation(SEED, population=20)
    series = compute_metrics_timeseries(engine)
    assert len(series) == 1
    assert series[0]["tick"] == 0
