"""Simulation lifecycle endpoints: start a new run, check status, advance
ticks. Bootstraps the initial population into Postgres directly (a
documented simplification, see SCOPE.md) and never lets Postgres/Kafka being
unavailable stop the simulation from starting or ticking (SRS §16, §18)."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from life100.api.dependencies import get_engine
from life100.api.state import state
from life100.db import crud
from life100.db.session import init_db, make_engine, make_session_factory
from life100.events.producer import InMemoryEventProducer, KafkaEventProducer
from life100.events.schemas import EventType
from life100.simulation.alternate_history import branch_simulation, compare_simulations
from life100.simulation.economy import run_tick
from life100.simulation.engine import HOURS_PER_DAY, SimulationEngine
from life100.simulation.setup import bootstrap_simulation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulation", tags=["simulation"])


class StartRequest(BaseModel):
    seed: int = 847291
    population: int = 100
    simulation_id: str = "sim_001"


class TickRequest(BaseModel):
    """`ticks` is the literal SRS §9 unit (1 tick = 1 simulated hour) --
    engine.tick advances by exactly this many hours. `days` is a convenience
    alternative (adds `days * 24` hours) so callers who think in days don't
    need to do the multiplication themselves; the two are additive."""

    ticks: int = 1
    days: int = 0


def _make_producer():
    broker = os.environ.get("KAFKA_BROKER")
    if not broker:
        return InMemoryEventProducer()
    try:
        return KafkaEventProducer(broker)
    except Exception:  # noqa: BLE001 — Kafka being unreachable must not block simulation start
        logger.warning("Kafka producer unavailable, falling back to in-memory (sim still runs)", exc_info=True)
        return InMemoryEventProducer()


@router.post("/start")
def start_simulation(payload: StartRequest) -> dict:
    producer = _make_producer()
    engine = bootstrap_simulation(
        payload.seed, population=payload.population, producer=producer, simulation_id=payload.simulation_id
    )
    state.engine = engine

    db_status = "skipped"
    try:
        db_engine = make_engine()
        init_db(db_engine)
        session_factory = make_session_factory(db_engine)
        with session_factory() as session:
            crud.bulk_upsert_initial_state(session, engine)
        state.db_session_factory = session_factory
        db_status = "loaded"
    except Exception:  # noqa: BLE001 — Postgres being unreachable must not block simulation start
        logger.warning("Postgres unavailable at simulation start; running in-memory only", exc_info=True)
        state.db_session_factory = None
        db_status = "unavailable"

    return {
        "simulation_id": engine.simulation_id,
        "seed": payload.seed,
        "population": len(engine.citizens),
        "households": len(engine.households),
        "businesses": len(engine.businesses),
        "postgres_bootstrap": db_status,
    }


@router.get("/status")
def simulation_status(engine: SimulationEngine = Depends(get_engine)) -> dict:
    """The single source for the dashboard's persistent civilization status
    bar (Level 1: "what is happening?") -- one call, computed here once,
    rather than every tab re-deriving unemployment/health-incident counts
    from raw citizens/events on its own."""
    working_age = [c for c in engine.citizens.values() if c.is_working_age()]
    unemployed = [c for c in working_age if c.occupation == "unemployed"]
    health_incidents = len(engine.log.of_type(EventType.MEDICAL_VISIT)) + len(
        engine.log.of_type(EventType.HEALTH_IMPACTED)
    )
    return {
        "simulation_id": engine.simulation_id,
        "tick": engine.tick,
        "day": engine.day,
        "food_price_index": round(engine.food_price_index, 4),
        "active_disasters": sorted(engine.active_disasters.keys()),
        "active_disasters_detail": {
            name: {
                "magnitude": info.get("magnitude"),
                "started_tick": info.get("started_tick"),
                "duration_ticks": info.get("duration_ticks"),
            }
            for name, info in engine.active_disasters.items()
        },
        "policies": dict(engine.policies),
        "population": len(engine.citizens),
        "events_logged": len(engine.log),
        "unemployment_rate": round(len(unemployed) / len(working_age), 4) if working_age else 0.0,
        "active_businesses": sum(1 for b in engine.businesses.values() if b.active),
        "health_incidents": health_incidents,
    }


@router.post("/tick")
def advance_tick(payload: TickRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    total_hours = payload.ticks + payload.days * HOURS_PER_DAY
    for _ in range(total_hours):
        run_tick(engine)
    return {
        "tick": engine.tick,
        "day": engine.day,
        "simulation_time": engine.current_simulation_time(),
        "food_price_index": round(engine.food_price_index, 4),
    }


class BranchRequest(BaseModel):
    new_simulation_id: str
    parent_simulation_id: str | None = None  # defaults to the currently active simulation


@router.post("/branch")
def branch(payload: BranchRequest) -> dict:
    """SRS §27 — snapshot the current (or a named) simulation into an
    independent branch that can then be nudged differently and compared."""
    parent_id = payload.parent_simulation_id or state.active_simulation_id
    if parent_id is None or parent_id not in state.simulations:
        raise HTTPException(status_code=400, detail="parent simulation not found; start one first")
    if payload.new_simulation_id in state.simulations:
        raise HTTPException(status_code=409, detail=f"simulation_id '{payload.new_simulation_id}' already exists")

    parent = state.simulations[parent_id]
    try:
        new_branch = branch_simulation(parent, payload.new_simulation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state.simulations[new_branch.simulation_id] = new_branch
    return {
        "simulation_id": new_branch.simulation_id,
        "parent_simulation_id": parent_id,
        "branch_point_tick": parent.tick,
        "branch_point_day": parent.day,
    }


@router.post("/activate/{simulation_id}")
def activate(simulation_id: str) -> dict:
    """Switch which simulation the existing tick/disaster/AI endpoints act
    on — lets a user apply a different intervention to each branch."""
    if simulation_id not in state.simulations:
        raise HTTPException(status_code=404, detail=f"simulation '{simulation_id}' not found")
    state.active_simulation_id = simulation_id
    return {"active_simulation_id": simulation_id}


@router.get("/list")
def list_simulations() -> dict:
    def _branch_info(eng: SimulationEngine) -> dict | None:
        info = getattr(eng, "branch_info", None)
        if info is None:
            return None
        return {
            "parent_simulation_id": info.parent_simulation_id,
            "branch_point_tick": info.branch_point_tick,
            "branch_point_day": info.branch_point_tick // HOURS_PER_DAY,
        }

    return {
        "active_simulation_id": state.active_simulation_id,
        "simulations": [
            {
                "simulation_id": sim_id,
                "tick": eng.tick,
                "day": eng.day,
                "population": len(eng.citizens),
                "branch_info": _branch_info(eng),
            }
            for sim_id, eng in state.simulations.items()
        ],
    }


@router.get("/compare")
def compare(simulation_a: str, simulation_b: str) -> dict:
    """SRS §28 (Timeline Comparison) / §29 (Butterfly Effect Analysis) —
    metrics for both branches plus the events that only happened in one of
    them. Feed any divergent event_id to GET /events/{id}/effects to trace
    how it propagated."""
    if simulation_a not in state.simulations or simulation_b not in state.simulations:
        raise HTTPException(status_code=404, detail="both simulation_a and simulation_b must exist")
    return compare_simulations(state.simulations[simulation_a], state.simulations[simulation_b])
