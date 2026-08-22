from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from life100.api.dependencies import get_engine
from life100.simulation.disasters import DEFAULT_DROUGHT_DURATION_TICKS, trigger_drought
from life100.simulation.engine import SimulationEngine

router = APIRouter(prefix="/disasters", tags=["disasters"])


class DroughtRequest(BaseModel):
    duration_ticks: int = DEFAULT_DROUGHT_DURATION_TICKS


@router.post("/drought")
def start_drought(payload: DroughtRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    event = trigger_drought(engine, duration_ticks=payload.duration_ticks)
    return {"event_id": event.event_id, "food_price_index": round(engine.food_price_index, 4)}
