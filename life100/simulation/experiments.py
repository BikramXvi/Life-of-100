"""The "What If?" Engine — the actual point of this project.

Branch one identical starting civilization into N parallel worlds, apply a
different intervention to each, run them for the same number of ticks, and
report a real, *measured* comparison against an untouched control. Every
number in the result comes from an actual simulation run — there is no
lookup table, no pre-written scenario outcome. The engine doesn't know what
will happen until it runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from life100.events.schemas import EventType
from life100.simulation import disasters
from life100.simulation.alternate_history import branch_simulation
from life100.simulation.economy import run_tick
from life100.simulation.engine import SimulationEngine

DISASTER_TRIGGERS = {
    "drought": disasters.trigger_drought,
    "food_shortage": disasters.trigger_food_shortage,
    "flood": disasters.trigger_flood,
    "earthquake": disasters.trigger_earthquake,
    "disease_outbreak": disasters.trigger_disease_outbreak,
    "economic_recession": disasters.trigger_economic_recession,
    "energy_crisis": disasters.trigger_energy_crisis,
}


@dataclass
class Scenario:
    name: str
    disaster: str | None = None
    disaster_duration: int = 30
    disaster_severity: float | None = None  # only meaningful for "drought"
    policies: dict[str, float] = field(default_factory=dict)
    emergency_employment: bool = False
    emergency_employment_boost: float = 0.3


def _slugify(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")[:40]


def _end_disaster_if_active(world: SimulationEngine, name: str) -> None:
    """A scenario needs to trigger a FRESH disaster on each branch, but the
    base simulation it branches from may itself already have one active
    (e.g. the user introduced a drought from City > Overview, then opened
    What If? Lab). Since `world` is a throwaway branch, it's safe to end
    its copy of that disaster first via the normal DISASTER_ENDED event
    (CLAUDE.md rule 4: still only through the event system) rather than
    letting the second trigger fail with "already active" -- the same fix
    already applied in sensitivity.py for the same underlying reason."""
    if name in world.active_disasters:
        world.emit(
            EventType.DISASTER_ENDED,
            source_entity=name,
            source_type="disaster",
            payload={"disaster_type": name},
        )


def _apply_scenario(scenario: Scenario, world: SimulationEngine) -> None:
    if scenario.disaster:
        trigger = DISASTER_TRIGGERS.get(scenario.disaster)
        if trigger is None:
            raise ValueError(f"unknown disaster '{scenario.disaster}'")
        _end_disaster_if_active(world, scenario.disaster)
        kwargs = {"duration_ticks": scenario.disaster_duration}
        if scenario.disaster == "drought" and scenario.disaster_severity is not None:
            kwargs["severity"] = scenario.disaster_severity
        trigger(world, **kwargs)

    for policy, value in scenario.policies.items():
        world.emit(
            EventType.POLICY_CHANGED,
            source_entity="government",
            source_type="government",
            payload={"policy": policy, "value": value, "rationale": f"experiment scenario: {scenario.name}"},
        )

    if scenario.emergency_employment:
        _end_disaster_if_active(world, "emergency_employment_program")
        disasters.trigger_emergency_employment_program(
            world,
            duration_ticks=scenario.disaster_duration,
            demand_boost=scenario.emergency_employment_boost,
        )


def _metrics(world: SimulationEngine) -> dict:
    citizens = [c for c in world.citizens.values() if c.alive]
    households = list(world.households.values())
    working_age = [c for c in citizens if c.is_working_age()]
    unemployed = [c for c in working_age if c.occupation == "unemployed"]
    employed = len(working_age) - len(unemployed)

    business_failures = len(world.log.of_type(EventType.BUSINESS_FAILED))
    health_incidents = len(world.log.of_type(EventType.MEDICAL_VISIT)) + len(
        world.log.of_type(EventType.HEALTH_IMPACTED)
    )
    avg_wealth = sum(c.savings - c.debt for c in citizens) / len(citizens) if citizens else 0.0
    avg_stress = sum(h.financial_stress for h in households) / len(households) if households else 0.0

    return {
        "population": len(citizens),
        "employment": employed,
        "unemployment_rate": round(len(unemployed) / len(working_age), 4) if working_age else 0.0,
        "food_price_index": round(world.food_price_index, 4),
        "business_failures": business_failures,
        "avg_household_wealth": round(avg_wealth, 2),
        "avg_household_stress": round(avg_stress, 4),
        "health_incidents": health_incidents,
    }


def _pct_change(scenario_value: float, control_value: float) -> float | None:
    if control_value == 0:
        return None
    return round((scenario_value - control_value) / abs(control_value) * 100, 2)


def run_experiment(base_engine: SimulationEngine, scenarios: list[Scenario], ticks: int) -> tuple[dict, dict[str, SimulationEngine]]:
    """Branches `base_engine` once per scenario PLUS one untouched control,
    all from the identical current state, runs every world for the same
    number of ticks, and returns (measured metrics + % change vs. control
    for each, {simulation_id: engine}). Nothing here is precomputed — every
    branch is a real simulation run started fresh from this call.

    The second return value hands back every world's actual engine so a
    caller (the API layer) can register them somewhere inspectable — the
    point of an experiment is that you can drill into *any* of the
    resulting worlds afterward, not just read a metrics summary.
    """
    worlds: dict[str, SimulationEngine] = {}

    control = branch_simulation(base_engine, f"{base_engine.simulation_id}_control_{_slugify('control')}")
    for _ in range(ticks):
        run_tick(control)
    control_metrics = _metrics(control)
    worlds[control.simulation_id] = control

    results = []
    for i, scenario in enumerate(scenarios):
        world = branch_simulation(base_engine, f"{base_engine.simulation_id}_exp{i}_{_slugify(scenario.name)}")
        _apply_scenario(scenario, world)
        for _ in range(ticks):
            run_tick(world)
        world_metrics = _metrics(world)
        worlds[world.simulation_id] = world
        results.append(
            {
                "name": scenario.name,
                "simulation_id": world.simulation_id,
                "metrics": world_metrics,
                "pct_change_vs_control": {
                    key: _pct_change(world_metrics[key], control_metrics[key])
                    for key in world_metrics
                    if isinstance(world_metrics[key], (int, float))
                },
            }
        )

    summary = {
        "ticks": ticks,
        "control": {"simulation_id": control.simulation_id, "metrics": control_metrics},
        "scenarios": results,
    }
    return summary, worlds
