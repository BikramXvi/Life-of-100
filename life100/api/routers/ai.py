from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from life100.agents import government, historian
from life100.agents.base import GeminiClientError
from life100.api.dependencies import get_engine
from life100.simulation.engine import SimulationEngine

router = APIRouter(prefix="/ai", tags=["ai"])


class HistorianRequest(BaseModel):
    citizen_id: str
    question: str


@router.post("/government/propose")
def government_propose(engine: SimulationEngine = Depends(get_engine)) -> dict:
    """Government Agent: analyzes the current economic snapshot and proposes
    one policy. The proposal is validated before it can change anything —
    see agents/validator.py and the AI_DECISION_* events this produces."""
    try:
        return government.propose_and_apply_policy(engine)
    except GeminiClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/historian/ask")
def historian_ask(payload: HistorianRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    """Historian Agent: answers a question about one citizen, grounded in
    that citizen's real event history. Rejects (502) if the model cites
    evidence that doesn't actually exist."""
    try:
        return historian.answer_question(payload.citizen_id, payload.question, engine.log)
    except historian.GroundingError as exc:
        raise HTTPException(status_code=502, detail=f"Historian answer failed grounding check: {exc}") from exc
    except GeminiClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
