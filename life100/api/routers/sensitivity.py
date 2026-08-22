"""Sensitivity analysis API surface — SRS reframing point 8: sweep an input
and look for a real tipping point, not a manufactured one. See
`life100/simulation/sensitivity.py` for the detection methodology."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from life100.api.dependencies import get_engine
from life100.simulation.engine import SimulationEngine
from life100.simulation.sensitivity import run_sensitivity_sweep

router = APIRouter(prefix="/experiments", tags=["experiments"])


class SensitivitySweepRequest(BaseModel):
    parameter: str = "drought_severity"
    values: list[float] | None = None
    disaster_duration: int = 30
    ticks: int = 15
    refine: bool = True


@router.post("/sensitivity")
def sensitivity_sweep(
    payload: SensitivitySweepRequest, engine: SimulationEngine = Depends(get_engine)
) -> dict:
    """Branches the CURRENT simulation once per swept value (plus, when a
    candidate tipping point is found, one refinement batch per detected
    metric), runs every branch for `ticks` days, and returns the full
    per-value metric curve plus a per-metric tipping-point verdict. A
    metric with no detected tipping point genuinely had a smooth response
    across the sweep — that is reported as `null`, never forced.
    """
    try:
        return run_sensitivity_sweep(
            engine,
            parameter=payload.parameter,
            values=payload.values,
            disaster_duration=payload.disaster_duration,
            ticks=payload.ticks,
            refine=payload.refine,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
