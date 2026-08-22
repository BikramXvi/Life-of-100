"""Process-wide simulation state for the API.

One running simulation per API process for this submission (see SCOPE.md) —
multi-simulation/session management is out of scope. `db_session_factory`
is set only if Postgres was reachable when the simulation started; the API
degrades to in-memory-only if it wasn't (SRS §17/§34: the API keeps working
even if the operational DB is briefly unavailable).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from life100.simulation.engine import SimulationEngine


@dataclass
class AppState:
    engine: SimulationEngine | None = None
    db_session_factory: sessionmaker[Session] | None = None


state = AppState()
