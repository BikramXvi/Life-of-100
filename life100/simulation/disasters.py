"""Disaster triggers. SRS §26 — all seven named disaster types.

Each trigger applies a direct, immediate "shock" (a price jump, a business
cash markdown, a citizen health hit — analogous to a real drought actually
destroying crops or an earthquake actually damaging a building), then gets
out of the way: the downstream consequences (layoffs, business failures,
stress) are always computed by economy.py's tick loop reacting to the
changed state, never hardcoded here (SRS §3.3's `if drought: raj.lose_job()`
anti-pattern). `broad_cost_shock`/`broad_demand_shock` (engine.py's
`broad_disaster_multipliers`) let most of these share one mechanism instead
of six bespoke ones; drought/food_shortage instead drive `food_price_index`
directly since that mechanism already existed and is demo-verified.
"""

from __future__ import annotations

import random

from life100.events.schemas import Event, EventType
from life100.simulation.engine import SimulationEngine

DEFAULT_DROUGHT_DURATION_TICKS = 20
DROUGHT_INITIAL_SHOCK = 1.4  # immediate +40% food-price jump on trigger


def _start_disaster(
    engine: SimulationEngine,
    name: str,
    duration_ticks: int,
    kind: str | None = None,
    magnitude: float = 0.0,
) -> Event:
    if name in engine.active_disasters:
        raise ValueError(f"A {name} is already active")
    return engine.emit(
        EventType.DISASTER_STARTED,
        source_entity=name,
        source_type="disaster",
        payload={"disaster_type": name, "duration_ticks": duration_ticks, "kind": kind, "magnitude": magnitude},
    )


def _food_price_shock(engine: SimulationEngine, shock_multiplier: float) -> None:
    old_index = engine.food_price_index
    new_index = min(old_index * shock_multiplier, 3.0)
    engine.emit(
        EventType.PRICE_CHANGED,
        source_entity="market_food",
        source_type="business",
        payload={"good": "food", "old_index": round(old_index, 4), "new_index": round(new_index, 4)},
    )


def trigger_drought(engine: SimulationEngine, duration_ticks: int = DEFAULT_DROUGHT_DURATION_TICKS) -> Event:
    started = _start_disaster(engine, "drought", duration_ticks)
    _food_price_shock(engine, DROUGHT_INITIAL_SHOCK)
    return started


def trigger_food_shortage(engine: SimulationEngine, duration_ticks: int = 15) -> Event:
    """A distribution/supply-chain shortage rather than a production
    failure -- same food_price_index mechanism as drought, sharper and
    shorter."""
    started = _start_disaster(engine, "food_shortage", duration_ticks)
    _food_price_shock(engine, 1.6)
    return started


def trigger_flood(
    engine: SimulationEngine,
    duration_ticks: int = 12,
    damage_fraction: float = 0.4,
    affected_share: float = 0.3,
) -> Event:
    """Direct property damage to a random subset of businesses, plus a
    moderate food-price shock (flooded cropland)."""
    started = _start_disaster(engine, "flood", duration_ticks)
    _food_price_shock(engine, 1.2)
    _damage_random_businesses(engine, "flood", damage_fraction, affected_share)
    return started


def trigger_earthquake(
    engine: SimulationEngine,
    duration_ticks: int = 10,
    damage_fraction: float = 0.7,
    affected_share: float = 0.25,
) -> Event:
    """Structural damage -- a stronger, more concentrated direct shock than
    a flood; some businesses may be damaged badly enough to fail outright
    (an immediate structural-collapse outcome, distinct from the gradual
    cost-pressure BUSINESS_FAILED path economy.py computes)."""
    started = _start_disaster(engine, "earthquake", duration_ticks)
    _damage_random_businesses(engine, "earthquake", damage_fraction, affected_share, allow_immediate_failure=True)
    return started


def trigger_disease_outbreak(
    engine: SimulationEngine,
    duration_ticks: int = 25,
    demand_magnitude: float = 0.3,
    affected_share: float = 0.35,
) -> Event:
    """Broad demand shock (a sick, cautious population spends less) plus an
    immediate health hit to a random subset of citizens; economy.py's
    existing stress/medical-visit machinery takes it from there."""
    started = _start_disaster(engine, "disease_outbreak", duration_ticks, kind="broad_demand_shock",
                                magnitude=demand_magnitude)
    rng = random.Random(engine.world.seed + engine.tick + 31)
    living = [c for c in engine.citizens.values() if c.alive]
    for citizen in rng.sample(living, k=max(1, int(len(living) * affected_share))):
        engine.emit(
            EventType.HEALTH_IMPACTED,
            source_entity=citizen.citizen_id,
            source_type="citizen",
            payload={
                "cause": "disease_outbreak",
                "health_delta": round(rng.uniform(0.15, 0.4), 3),
                "stress_delta": round(rng.uniform(0.1, 0.3), 3),
            },
        )
    return started


def trigger_economic_recession(
    engine: SimulationEngine,
    duration_ticks: int = 40,
    demand_magnitude: float = 0.35,
) -> Event:
    """A sustained, economy-wide demand shock -- no single direct target,
    just less money moving through the whole city for a long stretch."""
    return _start_disaster(engine, "economic_recession", duration_ticks, kind="broad_demand_shock",
                             magnitude=demand_magnitude)


def trigger_energy_crisis(
    engine: SimulationEngine,
    duration_ticks: int = 20,
    cost_magnitude: float = 0.5,
) -> Event:
    """Broad cost shock -- every business's non-payroll costs rise, not
    just food-sector ones (contrast with drought's food-specific cost
    channel)."""
    return _start_disaster(engine, "energy_crisis", duration_ticks, kind="broad_cost_shock",
                             magnitude=cost_magnitude)


def _damage_random_businesses(
    engine: SimulationEngine,
    disaster_name: str,
    damage_fraction: float,
    affected_share: float,
    allow_immediate_failure: bool = False,
) -> None:
    """Emits BUSINESS_CONTRACTED for a random subset of active businesses.

    Only emits the event — the actual cash markdown (and any resulting
    BUSINESS_FAILED) happens in engine.py's handler, not here. Disasters
    describe what happened; only the engine applies it (CLAUDE.md rule 4)."""
    rng = random.Random(engine.world.seed + engine.tick + hash(disaster_name) % 1000)
    active = [b for b in engine.businesses.values() if b.active]
    if not active:
        return
    affected = rng.sample(active, k=max(1, int(len(active) * affected_share)))
    for business in affected:
        engine.emit(
            EventType.BUSINESS_CONTRACTED,
            source_entity=business.business_id,
            source_type="business",
            payload={
                "reason": f"{disaster_name}_damage",
                "damage_fraction": damage_fraction,
                "allow_failure": allow_immediate_failure,
            },
        )
