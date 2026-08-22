from __future__ import annotations

from fastapi import HTTPException

from life100.api.state import state
from life100.simulation.engine import SimulationEngine


def get_engine() -> SimulationEngine:
    if state.engine is None:
        raise HTTPException(status_code=400, detail="Simulation not started. POST /simulation/start first.")
    return state.engine
