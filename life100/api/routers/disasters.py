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


def _handle(trigger_fn, engine: SimulationEngine, duration_ticks: int | None) -> dict:
    try:
        kwargs = {"duration_ticks": duration_ticks} if duration_ticks is not None else {}
        event = trigger_fn(engine, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"event_id": event.event_id, "food_price_index": round(engine.food_price_index, 4)}


@router.post("/drought")
def start_drought(payload: DroughtRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_drought, engine, payload.duration_ticks)


@router.post("/food-shortage")
def start_food_shortage(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_food_shortage, engine, payload.duration_ticks)


@router.post("/flood")
def start_flood(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_flood, engine, payload.duration_ticks)


@router.post("/earthquake")
def start_earthquake(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_earthquake, engine, payload.duration_ticks)


@router.post("/disease-outbreak")
def start_disease_outbreak(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_disease_outbreak, engine, payload.duration_ticks)


@router.post("/economic-recession")
def start_economic_recession(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_economic_recession, engine, payload.duration_ticks)


@router.post("/energy-crisis")
def start_energy_crisis(payload: DisasterRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    return _handle(disasters.trigger_energy_crisis, engine, payload.duration_ticks)


@router.get("/active")
def list_active_disasters(engine: SimulationEngine = Depends(get_engine)) -> dict:
    return {"active_disasters": engine.active_disasters}
