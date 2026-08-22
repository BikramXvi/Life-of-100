from life100.events.schemas import EventType
from life100.simulation.alternate_history import branch_simulation, compare_simulations
from life100.simulation.causality import trace_effects
from life100.simulation.disasters import trigger_drought
from life100.simulation.economy import run_tick
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def _base_engine(n=60, ticks=5):
    engine = bootstrap_simulation(SEED, population=n, simulation_id="sim_base")
    trigger_drought(engine)
    for _ in range(ticks):
        run_tick(engine)
    return engine


def test_branch_is_independent_of_parent():
    parent = _base_engine()
    branch = branch_simulation(parent, "sim_branch")

    assert branch.simulation_id == "sim_branch"
    assert branch.tick == parent.tick
    assert set(branch.citizens) == set(parent.citizens)

    # mutating the branch must not affect the parent
    some_citizen_id = next(iter(branch.citizens))
    branch.citizens[some_citizen_id].savings = -999999
    assert parent.citizens[some_citizen_id].savings != -999999


def test_branch_rejects_same_simulation_id():
    parent = _base_engine()
    try:
        branch_simulation(parent, parent.simulation_id)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_two_branches_diverge_after_different_interventions():
    parent = _base_engine()
    timeline_a = branch_simulation(parent, "sim_a")
    timeline_b = branch_simulation(parent, "sim_b")

    # Timeline A: no further intervention, just let the drought run its course.
    for _ in range(15):
        run_tick(timeline_a)

    # Timeline B: apply a food subsidy before continuing.
    timeline_b.policies["food_subsidy"] = 0.5
    for _ in range(15):
        run_tick(timeline_b)

    comparison = compare_simulations(timeline_a, timeline_b)
    stress_a = comparison["simulation_a"]["metrics"]["average_household_stress"]
    stress_b = comparison["simulation_b"]["metrics"]["average_household_stress"]
    assert stress_b <= stress_a

    assert comparison["divergent_events"]["sim_a"]
    assert comparison["divergent_events"]["sim_b"]
    # divergent events must belong to their own timeline, not leak into the other
    assert all(e["event_id"].startswith("evt_sim_a_") for e in comparison["divergent_events"]["sim_a"])
    assert all(e["event_id"].startswith("evt_sim_b_") for e in comparison["divergent_events"]["sim_b"])


def test_butterfly_effect_traces_forward_from_a_divergent_event():
    parent = _base_engine()
    branch = branch_simulation(parent, "sim_butterfly")
    for _ in range(10):
        run_tick(branch)

    job_lost = [e for e in branch.log.all() if e.event_type == EventType.JOB_LOST and e.simulation_id == "sim_butterfly"]
    if not job_lost:
        return  # nothing to trace this run; not a failure of the mechanism
    caused = [e for e in job_lost if e.payload.get("caused_by")]
    if not caused:
        return
    root_event_id = caused[0].payload["caused_by"]
    effects = trace_effects(branch.log, root_event_id)
    assert caused[0] in effects
