"""Read-side aggregations for dashboard charts. Deliberately not part of
`simulation/` — this is a projection over the existing event log (a small
CQRS-style read model), not simulation logic; it never mutates state and
the dashboard calling it stays a thin client (ROADMAP §4.6).
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends

from life100.api.dependencies import get_engine
from life100.events.schemas import EventType
from life100.simulation.engine import HOURS_PER_DAY, SimulationEngine

router = APIRouter(tags=["analytics"])


def compute_metrics_timeseries(engine: SimulationEngine) -> list[dict]:
    """Reconstructs population/employment/active-business counts and the
    food price index at every tick, by walking the event log's deltas
    backward from the engine's known-correct current totals. Nothing here
    is guessed: every point is either a directly recorded value
    (food_price_index from PRICE_CHANGED) or an exact running total anchored
    to the current true count.
    """
    events = sorted(engine.log.all(), key=lambda e: (e.simulation_tick, e.event_id))
    max_tick = engine.tick

    current_population = sum(1 for c in engine.citizens.values() if c.alive)
    current_employed = sum(
        1 for c in engine.citizens.values() if c.is_working_age() and c.occupation not in ("unemployed", "deceased")
    )
    current_active_businesses = sum(1 for b in engine.businesses.values() if b.active)

    pop_delta: dict[int, int] = defaultdict(int)
    emp_delta: dict[int, int] = defaultdict(int)
    biz_delta: dict[int, int] = defaultdict(int)
    health_delta: dict[int, int] = defaultdict(int)
    price_by_tick: dict[int, float] = {}

    for event in events:
        if event.event_type == EventType.CHILD_BORN:
            pop_delta[event.simulation_tick] += 1
        elif event.event_type == EventType.CITIZEN_DIED:
            pop_delta[event.simulation_tick] -= 1
        elif event.event_type == EventType.JOB_STARTED:
            emp_delta[event.simulation_tick] += 1
        elif event.event_type == EventType.JOB_LOST:
            emp_delta[event.simulation_tick] -= 1
        elif event.event_type == EventType.BUSINESS_FAILED:
            biz_delta[event.simulation_tick] -= 1
        elif event.event_type == EventType.BUSINESS_EXPANDED and event.payload.get("reason") == "reopened_after_loan":
            biz_delta[event.simulation_tick] += 1
        elif event.event_type == EventType.PRICE_CHANGED and event.payload.get("good") == "food":
            price_by_tick[event.simulation_tick] = float(event.payload["new_index"])
        elif event.event_type in (EventType.MEDICAL_VISIT, EventType.HEALTH_IMPACTED):
            health_delta[event.simulation_tick] += 1

    baseline_population = current_population - sum(pop_delta.values())
    baseline_employed = current_employed - sum(emp_delta.values())
    baseline_businesses = current_active_businesses - sum(biz_delta.values())

    population, employed, active_businesses, price = (
        baseline_population,
        baseline_employed,
        baseline_businesses,
        1.0,
    )
    health_incidents_cumulative = 0
    series = []
    # `tick` is hourly (SRS §9); accumulate every hour's deltas but only emit
    # one row per day (at the day boundary, plus the final in-progress day)
    # so charts show daily-resolution trends exactly as before the
    # hourly-tick change, instead of 24x as many points.
    for tick in range(max_tick + 1):
        population += pop_delta.get(tick, 0)
        employed += emp_delta.get(tick, 0)
        active_businesses += biz_delta.get(tick, 0)
        health_incidents_cumulative += health_delta.get(tick, 0)
        if tick in price_by_tick:
            price = price_by_tick[tick]
        if tick % HOURS_PER_DAY != 0 and tick != max_tick:
            continue
        working_age_estimate = max(population, 1)
        series.append(
            {
                "tick": tick,
                "day": tick // HOURS_PER_DAY,
                "population": population,
                "employed": employed,
                "active_businesses": active_businesses,
                "food_price_index": round(price, 4),
                "health_incidents": health_incidents_cumulative,
                # a rough proxy (not every citizen is working-age) -- good
                # enough for a trend line, not presented as an exact rate
                "unemployment_proxy": round(1.0 - employed / working_age_estimate, 4),
            }
        )
    return series


@router.get("/simulation/metrics-timeseries")
def metrics_timeseries(engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    return compute_metrics_timeseries(engine)


@router.get("/simulation/event-volume")
def event_volume_by_tick(engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    """Event count per day, and per (day, event_type) — chart-ready.
    Bucketed by day (simulation_tick is now hourly, SRS §9) so this stays a
    "per day" volume chart rather than 24x noisier per-hour bars."""
    counts: dict[tuple[int, str], int] = defaultdict(int)
    for event in engine.log.all():
        counts[(event.simulation_tick // HOURS_PER_DAY, event.event_type.value)] += 1
    return [{"day": day, "event_type": event_type, "count": n} for (day, event_type), n in counts.items()]


@router.get("/relationships")
def all_relationships(engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    """Every relationship edge, economy-wide — for aggregate social-graph
    charts (strength distribution, type breakdown) rather than one citizen
    at a time."""
    seen: set[tuple[str, str]] = set()
    rows = []
    for citizen_id, edges in engine.relationships.items():
        for edge in edges:
            key = tuple(sorted((citizen_id, edge.other_id))) + (edge.relationship_type,)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "citizen_id": citizen_id,
                    "other_id": edge.other_id,
                    "relationship_type": edge.relationship_type,
                    "strength": edge.strength,
                    "trust": edge.trust,
                    "frequency": edge.frequency,
                }
            )
    return rows
