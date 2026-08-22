from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from life100.api.dependencies import get_engine
from life100.simulation.business import Business
from life100.simulation.engine import SimulationEngine

router = APIRouter(prefix="/businesses", tags=["businesses"])


def _summary(business: Business) -> dict:
    return {
        "business_id": business.business_id,
        "industry": business.industry,
        "building_id": business.building_id,
        "headcount": business.headcount(),
        "cash": business.cash,
        "revenue": business.revenue,
        "expenses": business.expenses,
        "profit": business.profit,
        "debt": business.debt,
        "active": business.active,
    }


@router.get("")
def list_businesses(engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    return [_summary(b) for b in engine.businesses.values()]


@router.get("/{business_id}")
def get_business(business_id: str, engine: SimulationEngine = Depends(get_engine)) -> dict:
    business = engine.businesses.get(business_id)
    if business is None:
        raise HTTPException(status_code=404, detail=f"business {business_id} not found")
    return {**_summary(business), "employee_ids": business.employee_ids}
