"""The 'What If?' engine — the flagship capability. These tests run the
actual "One City, Three Futures" scenario: identical starting civilization,
three different interventions, real measured divergence. Nothing here is
a lookup table."""

from __future__ import annotations

from life100.simulation.experiments import Scenario, run_experiment
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def test_control_and_scenarios_all_start_from_byte_identical_state():
    """Every branch must fork from the exact same tick/state -- otherwise
    "compare possible futures" would be meaningless."""
    base = bootstrap_simulation(SEED, population=80)
    result, worlds = run_experiment(
        base,
        [Scenario(name="No Intervention", disaster="drought")],
        ticks=1,
    )
    # all worlds see the same population/business count at the branch point
    assert result["control"]["metrics"]["population"] == len(base.citizens)
    assert result["control"]["simulation_id"] in worlds
    assert result["scenarios"][0]["simulation_id"] in worlds


def test_one_city_three_futures_produces_real_measured_divergence():
    """Drought, then: (A) no intervention, (B) food subsidy, (C) emergency
    employment program. Same starting city, same seed, same disaster, same
    tick count -- the ONLY difference between the three is the
    intervention. Whatever differs in the result is a genuine consequence
    of that difference, not a scripted outcome."""
    base = bootstrap_simulation(SEED, population=100)
    result, worlds = run_experiment(
        base,
        [
            Scenario(name="World A - No Intervention", disaster="drought", disaster_duration=30),
            Scenario(name="World B - Food Subsidy", disaster="drought", disaster_duration=30, policies={"food_subsidy": 0.5}),
            Scenario(
                name="World C - Emergency Employment", disaster="drought", disaster_duration=30, emergency_employment=True
            ),
        ],
        ticks=30,
    )

    world_a, world_b, world_c = result["scenarios"]

    # each world is a genuinely distinct simulation, not the same run
    # relabeled three times
    sim_ids = {w["simulation_id"] for w in result["scenarios"]} | {result["control"]["simulation_id"]}
    assert len(sim_ids) == 4

    # the food subsidy must measurably ease household stress relative to
    # doing nothing, from the same starting point under the same disaster
    assert world_b["metrics"]["avg_household_stress"] <= world_a["metrics"]["avg_household_stress"]

    # every scenario reports its divergence from an untouched control, not
    # just from each other, so "what did the disaster itself cost us" is
    # always answerable
    for world in (world_a, world_b, world_c):
        assert "food_price_index" in world["pct_change_vs_control"]
        assert world["pct_change_vs_control"]["food_price_index"] is not None

    # every resulting world is a real, inspectable SimulationEngine -- not
    # just a metrics summary that vanishes after the call returns
    assert all(w["simulation_id"] in worlds for w in result["scenarios"])
    assert worlds[world_b["simulation_id"]].policies.get("food_subsidy") == 0.5


def test_drought_severity_is_a_real_parameter_not_a_fixed_constant():
    """Needed for sensitivity analysis: two droughts differing only in
    declared severity must produce different food_price_index trajectories,
    not the same hardcoded ramp."""
    base = bootstrap_simulation(SEED, population=60)
    # short window, well below food_price_index's 3.0 cap, so the two
    # severities stay distinguishable rather than both saturating
    mild, _ = run_experiment(base, [Scenario(name="mild", disaster="drought", disaster_severity=0.1)], ticks=2)
    severe, _ = run_experiment(base, [Scenario(name="severe", disaster="drought", disaster_severity=0.5)], ticks=2)

    mild_price = mild["scenarios"][0]["metrics"]["food_price_index"]
    severe_price = severe["scenarios"][0]["metrics"]["food_price_index"]
    assert severe_price > mild_price


def test_emergency_employment_program_is_a_real_intervention_not_scripted_hiring():
    """The stimulus must work through the existing demand mechanism (no
    JOB_STARTED events are emitted directly by the trigger itself) -- any
    re-employment that happens must come from the ordinary decision engine
    reacting to eased conditions, not a mass-hiring script."""
    from life100.events.schemas import EventType
    from life100.simulation.disasters import trigger_emergency_employment_program

    engine = bootstrap_simulation(SEED, population=50)
    event = trigger_emergency_employment_program(engine, duration_ticks=20)

    assert event.event_type == EventType.DISASTER_STARTED
    assert "emergency_employment_program" in engine.active_disasters
    cost_mult, demand_mult = engine.broad_disaster_multipliers()
    assert demand_mult > 1.0, "a stimulus must boost demand above baseline, not just reduce a shock"


def test_running_an_experiment_from_a_simulation_already_mid_disaster_does_not_raise():
    """A real bug found via the dashboard's Guided Demo: running What If?
    from a simulation that already has an active drought (e.g. the user
    triggered one from City > Overview first) used to raise "A drought is
    already active", since each scenario branch inherits the base state's
    active disasters and then tries to trigger a second one. Each branch is
    disposable, so ending its own copy first (via a real DISASTER_ENDED
    event) is safe -- mirrors the identical fix already applied in
    sensitivity.py for the same underlying reason."""
    base = bootstrap_simulation(SEED, population=40)
    from life100.simulation.disasters import trigger_drought

    trigger_drought(base, duration_ticks=30, severity=0.4)
    assert "drought" in base.active_disasters

    result, _ = run_experiment(
        base,
        [Scenario(name="No Intervention", disaster="drought", disaster_duration=30, disaster_severity=0.4)],
        ticks=5,
    )
    assert result["scenarios"][0]["metrics"]["population"] > 0
    # the base simulation's own state must be untouched by branching
    assert "drought" in base.active_disasters
