from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from life100.api.dependencies import get_engine
from life100.simulation import disasters
from life100.simulation.disasters import DEFAULT_DROUGHT_DURATION_TICKS
from life100.simulation.engine import SimulationEngine

router = APIRouter(prefix="/disasters", tags=["disasters"])


class DroughtRequest(BaseModel):
    duration_ticks: int = DEFAULT_DROUGHT_DURATION_TICKS


class DisasterRequest(BaseModel):
    duration_ticks: int | None = None


class FloodRequest(BaseModel):
    duration_ticks: int | None = None
    damage_fraction: float | None = None
    affected_share: float | None = None


class EarthquakeRequest(BaseModel):
    duration_ticks: int | None = None
    damage_fraction: float | None = None
    affected_share: float | None = None


def _handle(trigger_fn, engine: SimulationEngine, **kwargs) -> dict:
    try:
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        event = trigger_fn(engine, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"event_id": event.event_id, "food_price_index": round(engine.food_price_index, 4)}


@router.post("/drought")
def start_drought(payload: DroughtRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_drought, engine, duration_ticks=payload.duration_ticks)


@router.post("/food-shortage")
def start_food_shortage(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_food_shortage, engine, duration_ticks=payload.duration_ticks)


@router.post("/flood")
def start_flood(payload: FloodRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    """damage_fraction/affected_share are now exposed (previously only
    reachable by calling trigger_flood() directly in Python) -- see
    PROOF.md for why this matters: the structural-collapse failure path
    is only reachable at all once a caller can actually push the damage
    fraction high enough, close to a full wipeout."""
    return _handle(
        disasters.trigger_flood,
        engine,
        duration_ticks=payload.duration_ticks,
        damage_fraction=payload.damage_fraction,
        affected_share=payload.affected_share,
    )


@router.post("/earthquake")
def start_earthquake(payload: EarthquakeRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    """See flood's docstring above -- same reasoning."""
    return _handle(
        disasters.trigger_earthquake,
        engine,
        duration_ticks=payload.duration_ticks,
        damage_fraction=payload.damage_fraction,
        affected_share=payload.affected_share,
    )


@router.post("/disease-outbreak")
def start_disease_outbreak(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_disease_outbreak, engine, duration_ticks=payload.duration_ticks)


@router.post("/economic-recession")
def start_economic_recession(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_economic_recession, engine, duration_ticks=payload.duration_ticks)


@router.post("/energy-crisis")
def start_energy_crisis(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_energy_crisis, engine, duration_ticks=payload.duration_ticks)


@router.get("/active")
def list_active_disasters(engine: SimulationEngine = Depends(get_engine)) -> dict:
    return {"active_disasters": engine.active_disasters}
