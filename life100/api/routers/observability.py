"""Observability + reproducibility metadata. SRS §33, §35, §36."""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends

from life100.api.dependencies import get_engine
from life100.simulation.engine import SimulationEngine

router = APIRouter(tags=["observability"])

SIMULATION_VERSION = "0.1.0"  # matches pyproject.toml


@router.get("/observability/metrics")
def metrics(engine: SimulationEngine = Depends(get_engine)) -> dict:
    now = time.time()
    recent_ticks = [t for t in engine.tick_timestamps if now - t <= 60]
    ticks_per_second = round(len(recent_ticks) / 60, 4) if recent_ticks else 0.0

    process_metrics: dict[str, float | None] = {"cpu_percent": None, "memory_mb": None}
    try:
        import psutil  # optional dependency; degrade gracefully if unavailable

        process = psutil.Process(os.getpid())
        process_metrics = {
            "cpu_percent": process.cpu_percent(interval=0.05),
            "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
        }
    except ImportError:
        pass

    return {
        "simulation_id": engine.simulation_id,
        "current_simulation_time": engine.current_simulation_time(),
        "tick": engine.tick,
        "ticks_per_second_1min_avg": ticks_per_second,
        "events_total": len(engine.log),
        "active_citizens": sum(1 for c in engine.citizens.values() if c.alive),
        "active_businesses": sum(1 for b in engine.businesses.values() if b.active),
        "active_disasters": sorted(engine.active_disasters.keys()),
        **process_metrics,
    }


@router.get("/simulation/reproducibility")
def reproducibility(engine: SimulationEngine = Depends(get_engine)) -> dict:
    """SRS §35 — the parameters a run must record to be reproducible."""
    return {
        "simulation_id": engine.simulation_id,
        "seed": engine.world.seed,
        "initial_configuration": {
            "width": engine.world.config.width,
            "height": engine.world.config.height,
            "residential_ratio": engine.world.config.residential_ratio,
            "commercial_ratio": engine.world.config.commercial_ratio,
            "industrial_ratio": engine.world.config.industrial_ratio,
        },
        "population": len(engine.citizens),
        "simulation_version": SIMULATION_VERSION,
        "event_schema_version": 1,
        "ai_model": os.environ.get("GEMINI_MODEL", "gemini-3.6-flash"),
        "agent_configuration": {
            "government_agent": "agents/government.py",
            "historian_agent": "agents/historian.py",
            "business_agent": "agents/business.py",
            "household_agent": "agents/household.py",
        },
    }
