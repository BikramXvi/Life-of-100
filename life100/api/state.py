"""Process-wide simulation state for the API.

One running simulation per API process for this submission (see SCOPE.md) —
multi-simulation/session management is out of scope. `db_session_factory`
is set only if Postgres was reachable when the simulation started; the API
degrades to in-memory-only if it wasn't (SRS §17/§34: the API keeps working
even if the operational DB is briefly unavailable).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session, sessionmaker

from life100.simulation.engine import SimulationEngine


@dataclass
class AppState:
    """`simulations` is the full registry (needed for alternate-history
    branching/comparison, SRS §27-28); `engine` is a property over it for
    backward compatibility — every existing endpoint that reads/writes
    `state.engine` keeps working unchanged, while transparently also
    registering/selecting from `simulations`."""

    simulations: dict[str, SimulationEngine] = field(default_factory=dict)
    active_simulation_id: str | None = None
    db_session_factory: sessionmaker[Session] | None = None

    @property
    def engine(self) -> SimulationEngine | None:
        if self.active_simulation_id is None:
            return None
        return self.simulations.get(self.active_simulation_id)

    @engine.setter
    def engine(self, value: SimulationEngine | None) -> None:
        if value is None:
            self.active_simulation_id = None
            return
        self.simulations[value.simulation_id] = value
        self.active_simulation_id = value.simulation_id


state = AppState()
