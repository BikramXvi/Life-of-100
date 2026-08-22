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
from life100.simulation.alternate_history import branch_simulation, compare_simulations
from life100.simulation.economy import run_tick
from life100.simulation.engine import SimulationEngine
from life100.simulation.setup import bootstrap_simulation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulation", tags=["simulation"])


class StartRequest(BaseModel):
    seed: int = 847291
    population: int = 100
    simulation_id: str = "sim_001"


class TickRequest(BaseModel):
    ticks: int = 1


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
    return {
        "simulation_id": engine.simulation_id,
        "tick": engine.tick,
        "food_price_index": round(engine.food_price_index, 4),
        "active_disasters": sorted(engine.active_disasters.keys()),
        "policies": dict(engine.policies),
        "population": len(engine.citizens),
        "events_logged": len(engine.log),
    }


@router.post("/tick")
def advance_tick(payload: TickRequest, engine: SimulationEngine = Depends(get_engine)) -> dict:
    for _ in range(payload.ticks):
        run_tick(engine)
    return {"tick": engine.tick, "food_price_index": round(engine.food_price_index, 4)}


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
    return {
        "active_simulation_id": state.active_simulation_id,
        "simulations": [
            {"simulation_id": sim_id, "tick": eng.tick, "population": len(eng.citizens)}
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
