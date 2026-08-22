"""Disaster triggers. SRS §26.

Only drought is implemented for this submission (see SCOPE.md) — it's
enough to demonstrate that a disaster's downstream effects are emergent
(computed by economy.py tick-over-tick) rather than scripted
(`if drought: raj.lose_job()` is explicitly what SRS §3.3 says to avoid).
"""

from __future__ import annotations

from life100.events.schemas import Event, EventType
from life100.simulation.engine import SimulationEngine

DEFAULT_DROUGHT_DURATION_TICKS = 20
DROUGHT_INITIAL_SHOCK = 1.4  # immediate +40% food-price jump on trigger


def trigger_drought(engine: SimulationEngine, duration_ticks: int = DEFAULT_DROUGHT_DURATION_TICKS) -> Event:
    if "drought" in engine.active_disasters:
        raise ValueError("A drought is already active")

    started = engine.emit(
        EventType.DISASTER_STARTED,
        source_entity="drought",
        source_type="disaster",
        payload={"disaster_type": "drought", "duration_ticks": duration_ticks},
    )

    old_index = engine.food_price_index
    new_index = min(old_index * DROUGHT_INITIAL_SHOCK, 3.0)
    engine.emit(
        EventType.PRICE_CHANGED,
        source_entity="market_food",
        source_type="business",
        payload={"good": "food", "old_index": round(old_index, 4), "new_index": round(new_index, 4)},
    )

    return started
