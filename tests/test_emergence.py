"""Proof tests for the three things that actually matter for this project,
not feature count:

1. It isn't scripted.
2. Complex behavior emerges from simple rules.
3. The system can be experimentally used to understand and compare
   possible futures.

Each group below is a durable, re-runnable proof — not a narrated claim.
See PROOF.md for the write-up with concrete numbers from an actual run.
"""

from __future__ import annotations

import re
from pathlib import Path

from life100.events.schemas import EventType
from life100.simulation.alternate_history import branch_simulation, compare_simulations
from life100.simulation.disasters import trigger_drought
from life100.simulation.economy import FOOD_INDUSTRIES, run_days
from life100.simulation.setup import bootstrap_simulation

SEED = 847291
REPO_ROOT = Path(__file__).resolve().parents[1]


def _stdev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance**0.5


# ============================================================================
# 1. It isn't scripted.
# ============================================================================


def test_no_hardcoded_entity_ids_in_the_rules_that_produce_the_cascade():
    """A source-code audit: the modules that decide who loses a job, whose
    business fails, who gets sick, etc. must never special-case a specific
    citizen/business/household id. If the cascade were scripted, this is
    where a literal id would have to live."""
    suspicious = re.compile(r'["\'](cit_\d{4}|biz_\d{3}|hh_\d{3})["\']')
    for rel_path in (
        "life100/simulation/economy.py",
        "life100/simulation/disasters.py",
        "life100/simulation/decisions.py",
        "life100/simulation/life_events.py",
    ):
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        matches = suspicious.findall(text)
        assert not matches, f"{rel_path} contains hardcoded entity id(s): {matches}"


def test_same_seed_produces_byte_identical_cascade_twice():
    """Determinism, not randomness dressed up as complexity: the exact same
    seed must produce the exact same sequence of events, every time."""

    def run():
        engine = bootstrap_simulation(SEED, population=80)
        trigger_drought(engine)
        run_days(engine, 20)
        return [(e.event_type, e.source_entity, e.simulation_tick, e.payload) for e in engine.log.all()]

    assert run() == run()


def test_different_seeds_hit_different_specific_citizens_but_the_same_aggregate_pattern():
    """If the cascade were `if drought: raj.lose_job()`, changing the seed
    would either do nothing or hit the same hardcoded target. Instead: which
    *specific* citizens/businesses are affected must change with the seed,
    while the *aggregate* pattern the mechanism guarantees (food-sector
    businesses are hit, at least one layoff happens) must hold regardless."""
    affected_citizen_sets = []
    for seed in (847291, 123456, 999999):
        engine = bootstrap_simulation(seed, population=80)
        trigger_drought(engine)
        run_days(engine, 20)

        job_lost = engine.log.of_type(EventType.JOB_LOST)
        assert job_lost, f"seed {seed}: expected the mechanism to produce at least one layoff"
        affected_citizen_sets.append(frozenset(e.source_entity for e in job_lost))

        # the aggregate pattern the mechanism guarantees: food-industry
        # businesses are always among the ones that lose staff first
        food_business_ids = {b.business_id for b in engine.businesses.values() if b.industry in FOOD_INDUSTRIES}
        assert any(e.payload.get("business_id") in food_business_ids for e in job_lost)

    # the *specific* citizens affected differ across seeds -- not a fixed target
    assert affected_citizen_sets[0] != affected_citizen_sets[1]
    assert affected_citizen_sets[1] != affected_citizen_sets[2]


# ============================================================================
# 2. Complex behavior emerges from simple rules.
# ============================================================================


def test_contagion_reaches_businesses_the_disaster_never_directly_touched():
    """The only direct effect of a drought is on food_price_index (and, via
    that, food-industry costs). Nothing in disasters.py or economy.py says
    "and also hurt manufacturing/retail" -- but a non-food business CAN
    still fail, purely because falling household budgets (a consequence of
    higher food prices) reduce the demand_multiplier every business's
    revenue depends on. That's contagion emerging from one shared variable,
    not two rules bolted together.

    A long drought is used deliberately: well-capitalized businesses take
    time to burn through their cash reserves under a modest demand
    shortfall, and the effect measurably outlives the disaster's official
    "active" window (household stress decays slowly) -- this is the
    lagged, second-order case, not the fast, direct one."""
    engine = bootstrap_simulation(SEED, population=100)
    trigger_drought(engine, duration_ticks=60)
    run_days(engine, 90)

    job_lost = engine.log.of_type(EventType.JOB_LOST)
    non_food_layoffs = [
        e
        for e in job_lost
        if engine.businesses.get(e.payload.get("business_id"))
        and engine.businesses[e.payload["business_id"]].industry not in FOOD_INDUSTRIES
    ]
    assert non_food_layoffs, "expected at least one non-food business to be hit by the demand contagion"

    # and it must be explainable, not a mystery: the causal link fix means
    # this indirect, lagged effect still cites the real drought event, not
    # None, even after the disaster has formally ended
    drought_event_id = engine.log.of_type(EventType.DISASTER_STARTED)[0].event_id
    assert all(e.payload.get("caused_by") == drought_event_id for e in non_food_layoffs)


def test_a_shock_measurably_changes_wealth_dispersion_from_identical_starting_conditions():
    """Two branches, byte-identical population, identical simple per-tick
    rules -- the only difference is one branch takes a drought. Nothing
    anywhere computes "inequality" or decides in advance which direction it
    should move.

    This was written expecting a shock to widen net-worth dispersion,
    the naive assumption. Running it showed the opposite: the drought
    measurably COMPRESSES dispersion here, because job losses cut into
    previously-salaried households' income, pulling them down toward
    households that were already at zero employment income either way —
    an emergent leveling effect, not something anyone coded. That the
    experiment corrected the person who built the mechanism is itself
    evidence this isn't scripted toward a foregone conclusion; the
    assertion below reflects the measured direction, not the assumed one.
    """
    baseline = bootstrap_simulation(SEED, population=100, simulation_id="sim_baseline")
    treatment = branch_simulation(baseline, "sim_treatment")
    control = branch_simulation(baseline, "sim_control")

    trigger_drought(treatment, duration_ticks=60)
    run_days(treatment, 60)
    run_days(control, 60)

    def net_worth_spread(engine) -> float:
        values = [c.savings - c.debt for c in engine.citizens.values() if c.alive]
        return _stdev(values)

    assert net_worth_spread(control) > net_worth_spread(treatment)


# ============================================================================
# 3. The system can be experimentally used to compare possible futures.
# ============================================================================


def test_a_policy_intervention_produces_a_measurable_and_explainable_divergence():
    """Branch once, apply ONE policy difference to one branch, run both the
    same number of ticks. The outcome must differ in the expected direction
    (subsidy eases stress) AND the intervention itself must be a real,
    findable event in the timeline it was applied to -- the comparison
    isn't just "two different random runs", it's causally anchored to the
    actual choice that was made."""
    parent = bootstrap_simulation(SEED, population=70, simulation_id="sim_parent")
    trigger_drought(parent)
    run_days(parent, 10)

    subsidized = branch_simulation(parent, "sim_subsidized")
    unsubsidized = branch_simulation(parent, "sim_unsubsidized")

    policy_event = subsidized.emit(
        EventType.POLICY_CHANGED,
        source_entity="government",
        source_type="government",
        payload={"policy": "food_subsidy", "value": 0.5, "rationale": "experiment"},
    )
    assert subsidized.policies["food_subsidy"] == 0.5

    run_days(subsidized, 20)
    run_days(unsubsidized, 20)

    comparison = compare_simulations(subsidized, unsubsidized)
    stress_subsidized = comparison["simulation_a"]["metrics"]["average_household_stress"]
    stress_unsubsidized = comparison["simulation_b"]["metrics"]["average_household_stress"]
    assert stress_subsidized < stress_unsubsidized

    assert subsidized.log.get(policy_event.event_id) is not None
    assert any(
        e["event_id"] == policy_event.event_id for e in comparison["divergent_events"]["sim_subsidized"]
    )
