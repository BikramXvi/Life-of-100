from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from life100.api.dependencies import get_engine
from life100.simulation import causality
from life100.simulation.engine import SimulationEngine

router = APIRouter(tags=["events"])


@router.get("/events")
def recent_events(limit: int = 50, engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    return [e.model_dump() for e in engine.log.recent(limit)]


@router.get("/events/{event_id}/causes")
def event_causes(event_id: str, engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    """SRS §22-23 — the explicit causal chain leading to this event (only
    ever real, recorded links; never an inferred/fabricated graph)."""
    if engine.log.get(event_id) is None:
        raise HTTPException(status_code=404, detail=f"event {event_id} not found")
    return [e.model_dump() for e in causality.trace_causes(engine.log, event_id)]


@router.get("/events/{event_id}/effects")
def event_effects(event_id: str, engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    """The events that explicitly cite this one as their cause."""
    if engine.log.get(event_id) is None:
        raise HTTPException(status_code=404, detail=f"event {event_id} not found")
    return [e.model_dump() for e in causality.trace_effects(engine.log, event_id)]


@router.get("/citizens/{citizen_id}/timeline")
def citizen_timeline(citizen_id: str, engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    """A citizen's full, chronological, replayable event history (SRS §24)."""
    return [e.model_dump() for e in engine.log.for_entity(citizen_id)]
