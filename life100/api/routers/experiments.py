"""The "What If?" Engine's API surface. This is the actual point of the
project: branch the current civilization into N parallel worlds, apply a
different intervention to each, run them, and report what really happened —
not a lookup table."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from life100.api.dependencies import get_engine
from life100.api.state import state
from life100.simulation.engine import SimulationEngine
from life100.simulation.experiments import Scenario, run_experiment

router = APIRouter(prefix="/experiments", tags=["experiments"])


class ScenarioRequest(BaseModel):
    name: str
    disaster: str | None = None
    disaster_duration: int = 30
    disaster_severity: float | None = None
    policies: dict[str, float] = {}
    emergency_employment: bool = False
    emergency_employment_boost: float = 0.3


class ExperimentRequest(BaseModel):
    scenarios: list[ScenarioRequest]
    ticks: int = 30


@router.post("/run")
def run(payload: ExperimentRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    """Branches the CURRENT simulation state into one control + one branch
    per requested scenario, runs every world for `ticks` days, and returns
    measured metrics + % change vs. an untouched control for each. Every
    branch is a real, independent SimulationEngine — inspect any of them
    afterward via GET /simulation/list, GET /citizens?simulation_id=...,
    or POST /simulation/activate/{id}.
    """
    if not payload.scenarios:
        raise HTTPException(status_code=400, detail="at least one scenario is required")
    scenarios = [
        Scenario(
            name=s.name,
            disaster=s.disaster,
            disaster_duration=s.disaster_duration,
            disaster_severity=s.disaster_severity,
            policies=s.policies,
            emergency_employment=s.emergency_employment,
            emergency_employment_boost=s.emergency_employment_boost,
        )
        for s in payload.scenarios
    ]
    try:
        summary, worlds = run_experiment(engine, scenarios, payload.ticks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # register every resulting world so it's independently inspectable
    # afterward (GET /simulation/list, POST /simulation/activate/{id}, or
    # any citizens/events/causality endpoint once activated) -- an
    # experiment's point is that you can drill into any of its outcomes,
    # not just read a metrics summary.
    state.simulations.update(worlds)
    return summary
