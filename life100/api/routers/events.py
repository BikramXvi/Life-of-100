from __future__ import annotations

from fastapi import APIRouter, Depends

from life100.api.dependencies import get_engine
from life100.simulation.engine import SimulationEngine

router = APIRouter(tags=["events"])


@router.get("/events")
def recent_events(limit: int = 50, engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    return [e.model_dump() for e in engine.log.recent(limit)]


@router.get("/citizens/{citizen_id}/timeline")
def citizen_timeline(citizen_id: str, engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    """A citizen's full, chronological, replayable event history (SRS §24)."""
    return [e.model_dump() for e in engine.log.for_entity(citizen_id)]
