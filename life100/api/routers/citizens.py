from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from life100.api.dependencies import get_engine
from life100.simulation import memory
from life100.simulation.citizens import Citizen
from life100.simulation.engine import SimulationEngine

router = APIRouter(prefix="/citizens", tags=["citizens"])


def _summary(citizen: Citizen) -> dict:
    return {
        "citizen_id": citizen.citizen_id,
        "name": citizen.name,
        "age": citizen.age,
        "gender": citizen.gender,
        "household_id": citizen.household_id,
        "occupation": citizen.occupation,
        "employer_id": citizen.employer_id,
        "salary": citizen.salary,
        "savings": citizen.savings,
        "debt": citizen.debt,
        "health_score": citizen.health_score,
        "stress": citizen.stress,
        "alive": citizen.alive,
    }


@router.get("")
def list_citizens(engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    return [_summary(c) for c in engine.citizens.values()]


@router.get("/{citizen_id}")
def get_citizen(citizen_id: str, engine: SimulationEngine = Depends(get_engine)) -> dict:
    citizen = engine.citizens.get(citizen_id)
    if citizen is None:
        raise HTTPException(status_code=404, detail=f"citizen {citizen_id} not found")

    household = engine.households.get(citizen.household_id) if citizen.household_id else None
    business = engine.businesses.get(citizen.employer_id) if citizen.employer_id else None

    return {
        **_summary(citizen),
        "personality": vars(citizen.personality),
        "goals": vars(citizen.goals) if citizen.goals else None,
        "spouse_id": citizen.spouse_id,
        "parent_ids": citizen.parent_ids,
        "children_ids": citizen.children_ids,
        "marital_status": citizen.marital_status,
        "household": (
            {"household_id": household.household_id, "member_ids": household.member_ids} if household else None
        ),
        "employer": (
            {"business_id": business.business_id, "industry": business.industry} if business else None
        ),
    }


@router.get("/{citizen_id}/memories")
def get_memories(citizen_id: str, engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    """SRS §25 — curated significant life events (first job, marriage,
    birth of a child, business failure, death of a family member, ...),
    computed on demand from the same event log the Historian Agent uses."""
    if citizen_id not in engine.citizens:
        raise HTTPException(status_code=404, detail=f"citizen {citizen_id} not found")
    return memory.get_memories(engine, citizen_id)


@router.get("/{citizen_id}/relationships")
def get_relationships(citizen_id: str, engine: SimulationEngine = Depends(get_engine)) -> list[dict]:
    """SRS §12 — this citizen's social relationship graph edges."""
    if citizen_id not in engine.citizens:
        raise HTTPException(status_code=404, detail=f"citizen {citizen_id} not found")
    edges = engine.relationships.get(citizen_id, [])
    return [
        {
            "other_id": r.other_id,
            "other_name": engine.citizens[r.other_id].name if r.other_id in engine.citizens else None,
            "relationship_type": r.relationship_type,
            "strength": r.strength,
            "trust": r.trust,
            "frequency": r.frequency,
        }
        for r in edges
    ]
