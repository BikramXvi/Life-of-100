from life100.events.schemas import EventType
from life100.simulation.disasters import (
    trigger_disease_outbreak,
    trigger_earthquake,
    trigger_economic_recession,
    trigger_energy_crisis,
    trigger_flood,
    trigger_food_shortage,
)
from life100.simulation.economy import run_tick
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def _engine(n=60):
    return bootstrap_simulation(SEED, population=n)


def test_food_shortage_raises_food_price_immediately():
    engine = _engine()
    baseline = engine.food_price_index
    trigger_food_shortage(engine)
    assert engine.food_price_index > baseline


def test_flood_damages_some_businesses_via_events_not_direct_mutation():
    engine = _engine()
    cash_before = {b.business_id: b.cash for b in engine.businesses.values()}
    trigger_flood(engine)
    contracted = engine.log.of_type(EventType.BUSINESS_CONTRACTED)
    assert contracted, "expected at least one BUSINESS_CONTRACTED event"
    for event in contracted:
        business = engine.businesses[event.source_entity]
        assert business.cash < cash_before[business.business_id]


def test_earthquake_can_fail_businesses_outright():
    engine = _engine()
    trigger_earthquake(engine, damage_fraction=1.0, affected_share=0.5)
    failed = engine.log.of_type(EventType.BUSINESS_FAILED)
    assert failed, "expected at least one immediate structural failure from a severe earthquake"
    for event in failed:
        assert engine.businesses[event.source_entity].active is False


def test_disease_outbreak_emits_health_impacted_events_and_reduces_health():
    engine = _engine()
    citizens = list(engine.citizens.values())
    health_before = {c.citizen_id: c.health_score for c in citizens}
    trigger_disease_outbreak(engine, affected_share=0.5)
    impacted = engine.log.of_type(EventType.HEALTH_IMPACTED)
    assert impacted
    for event in impacted:
        citizen = engine.citizens[event.source_entity]
        assert citizen.health_score < health_before[citizen.citizen_id]
    assert "disease_outbreak" in engine.active_disasters
    assert engine.active_disasters["disease_outbreak"]["kind"] == "broad_demand_shock"


def test_economic_recession_and_energy_crisis_register_as_broad_shocks():
    engine = _engine()
    trigger_economic_recession(engine)
    trigger_energy_crisis(engine)
    cost_mult, demand_mult = engine.broad_disaster_multipliers()
    assert demand_mult < 1.0
    assert cost_mult > 1.0


def test_multiple_disasters_can_be_active_and_expire_independently():
    engine = _engine()
    trigger_economic_recession(engine, duration_ticks=5)
    trigger_energy_crisis(engine, duration_ticks=50)
    for _ in range(6):
        run_tick(engine)
    assert "economic_recession" not in engine.active_disasters
    assert "energy_crisis" in engine.active_disasters
