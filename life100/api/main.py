"""LIFE/100 FastAPI application — the primary interface for this
submission (see SCOPE.md). Auto-generated docs at /docs."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402 — must follow load_dotenv()
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from life100.api.routers import (  # noqa: E402
    ai,
    analytics,
    businesses,
    citizens,
    disasters,
    events,
    experiments,
    households,
    observability,
    sensitivity,
    simulation,
    warehouse,
    world,
)

app = FastAPI(
    title="LIFE/100 API",
    description=(
        "A depth-first, ~100-citizen digital society simulation. "
        "Only 100 people. Every life matters."
    ),
    version="0.1.0",
)

# No cookies/auth on this API (see agents/base.py, api/state.py) -- a wide-open
# CORS policy is the pragmatic choice for a local research/demo tool served
# behind a tunnel, rather than an allowlist that breaks every time the
# frontend's dev-server port or tunnel hostname changes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation.router)
app.include_router(citizens.router)
app.include_router(businesses.router)
app.include_router(households.router)
app.include_router(events.router)
app.include_router(disasters.router)
app.include_router(ai.router)
app.include_router(warehouse.router)
app.include_router(observability.router)
app.include_router(world.router)
app.include_router(experiments.router)
app.include_router(sensitivity.router)
app.include_router(analytics.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
