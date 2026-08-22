"""SRS §30.3 — a dedicated Household endpoint (previously the dashboard
derived household rows purely from citizen records, missing Household's own
fields like `home_building_id`, `property_value`, `goals`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from life100.api.dependencies import get_engine
from life100.simulation.engine import SimulationEngine
from life100.simulation.households import Household

router = APIRouter(prefix="/households", tags=["households"])


def _summary(household: Household) -> dict:
    return {
        "household_id": household.household_id,
        "member_ids": household.member_ids,
        "home_building_id": household.home_building_id,
        "property_value": household.property_value,
        "income": household.income,
        "expenses": household.expenses,
        "savings": household.savings,
        "debt": household.debt,
        "assets": household.assets,
        "goals": household.goals,
        "financial_stress": household.financial_stress,
        "living_conditions": household.living_conditions,
    }


@router.get("")
def list_households(engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    return [_summary(h) for h in engine.households.values()]


@router.get("/{household_id}")
def get_household(household_id: str, engine: SimulationEngine = Depends(get_engine)) -> dict:
    household = engine.households.get(household_id)
    if household is None:
        raise HTTPException(status_code=404, detail=f"household {household_id} not found")
    return _summary(household)
