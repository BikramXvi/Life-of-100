"""Simulation lifecycle endpoints: start a new run, check status, advance
ticks. Bootstraps the initial population into Postgres directly (a
documented simplification, see SCOPE.md) and never lets Postgres/Kafka being
unavailable stop the simulation from starting or ticking (SRS §16, §18)."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from life100.api.dependencies import get_engine
from life100.api.state import state
from life100.db import crud
from life100.db.session import init_db, make_engine, make_session_factory
from life100.events.producer import InMemoryEventProducer, KafkaEventProducer
from life100.simulation.business import generate_businesses
from life100.simulation.economy import run_tick
from life100.simulation.engine import SimulationEngine
from life100.simulation.households import generate_population
from life100.simulation.world import WorldConfig, generate_world

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
    world = generate_world(WorldConfig(seed=payload.seed))
    citizens, households = generate_population(payload.seed, n=payload.population)
    businesses = generate_businesses(payload.seed, world, citizens)

    producer = _make_producer()
    engine = SimulationEngine(
        world, citizens, households, businesses, producer=producer, simulation_id=payload.simulation_id
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
