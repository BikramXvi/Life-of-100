"""SRS §30.1 — World View data. Returns the zone grid and buildings with
their (x, y) coordinates so a client can render an actual map, rather than
just tables of entity attributes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from life100.api.dependencies import get_engine
from life100.simulation.engine import SimulationEngine

router = APIRouter(prefix="/world", tags=["world"])


@router.get("")
def get_world(engine: SimulationEngine = Depends(get_engine)) -> dict:
    return {
        "city_id": engine.world.city_id,
        "seed": engine.world.seed,
        "width": engine.world.config.width,
        "height": engine.world.config.height,
        "zones": [{"x": z.x, "y": z.y, "kind": z.kind} for z in engine.world.zones],
        "buildings": [
            {"building_id": b.building_id, "x": b.x, "y": b.y, "kind": b.kind} for b in engine.world.buildings
        ],
    }
