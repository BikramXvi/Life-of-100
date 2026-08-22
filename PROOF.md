# PROOF.md — The three things that actually matter

Feature count doesn't make this project real. Three specific properties do:

1. **It isn't scripted.**
2. **Complex behavior emerges from simple rules.**
3. **The system can be experimentally used to understand and compare possible futures.**

Everything below is backed by a durable, re-runnable test in `tests/test_emergence.py` — not a
narrated claim. Run `uv run pytest tests/test_emergence.py -v` to verify all of it yourself. The
numbers quoted here are from actual runs against `seed=847291`, reproduced while writing this
document.

---

## 1. It isn't scripted

**The audit** (`test_no_hardcoded_entity_ids_in_the_rules_that_produce_the_cascade`): the modules
that decide who loses a job, whose business fails, who gets sick — `economy.py`, `disasters.py`,
`decisions.py`, `life_events.py` — contain **zero** literal citizen/business/household IDs. If
the cascade were `if drought: raj.lose_job()`, that's exactly where it would have to live. It
doesn't.

**Determinism, not randomness dressed up as complexity**
(`test_same_seed_produces_byte_identical_cascade_twice`): the same seed run twice produces the
exact same event sequence — type, entity, tick, and payload, all identical. This matters because
"unscripted" doesn't mean "random noise"; it means the outcome is *computed*, and computation is
reproducible.

**Different seeds hit different specific people, but the same underlying pattern holds**
(`test_different_seeds_hit_different_specific_citizens_but_the_same_aggregate_pattern`): three
different seeds, same drought, same tick count. The *specific* citizens who lose their jobs are
different in every run — that's expected of a real generative population, not a fixed target.
What's *invariant* across all three seeds is the pattern the mechanism actually guarantees: at
least one food-industry business is always among the first hit, because that's the one thing the
mechanism (not a script) directly determines.

---

## 2. Complex behavior emerges from simple rules

The entire economic mechanism is: a business's revenue depends on headcount and an aggregate
demand multiplier; its expenses depend on payroll and a cost multiplier; if cash goes negative, it
sheds staff. A household's budget is income minus a food-price-scaled cost of living. That's it —
no rule anywhere mentions "contagion," "inequality," or "recovery." Two things emerge from that
alone:

**Contagion to businesses the disaster never touched**
(`test_contagion_reaches_businesses_the_disaster_never_directly_touched`): a drought's only
*direct* effect is on `food_price_index`. But `demand_multiplier` — which every business's
revenue depends on, food or not — is driven by average household financial stress, which the
drought raises through everyone's higher cost of living. Running a 60-tick drought for 90 total
ticks produces **19 layoffs at non-food businesses** (manufacturing, retail) that were never the
disaster's target. This is contagion through one shared variable, not two rules bolted together.

It gets more interesting: those 19 layoffs happen at ticks 65–90+, well *after* the drought's
official 60-tick "active" window ends at tick 60. The effect **outlives the disaster**, because
household stress decays slowly. Writing the explainability check for this exposed a real gap —
the original `caused_by` logic only looked at *currently active* disasters, so these lagged,
second-order layoffs were showing up with **no recorded cause at all**. Fixed by having the
engine remember the most recent disaster's event even after it ends
(`engine.last_disaster_event_id`), and citing it whenever stress is still elevated enough to
plausibly be the reason. All 19 now correctly trace back to the real `DISASTER_STARTED` event —
verified, not assumed.

**A shock changes wealth dispersion — in the direction I didn't expect**
(`test_a_shock_measurably_changes_wealth_dispersion_from_identical_starting_conditions`): branch
the same population twice, apply a drought to only one branch, run both 60 ticks under otherwise
identical rules. I wrote this test expecting a shock to *widen* inequality — the naive
assumption. The actual measurement:

| Tick | Treatment (drought) net-worth spread | Control net-worth spread | Difference |
|---|---|---|---|
| 10 | 16,106 | 16,135 | −28 |
| 20 | 15,989 | 16,080 | −91 |
| 30 | 15,826 | 15,999 | −172 |
| 40 | 15,652 | 15,923 | −271 |
| 50 | 15,467 | 15,822 | −354 |
| 60 | 15,298 | 15,734 | −436 |

The drought **compresses** dispersion, monotonically, the opposite of my hypothesis. The
mechanism: job losses cut into previously-salaried households' income, pulling them down toward
households that already had zero employment income either way — a leveling effect that emerges
from the same simple rules, not something anyone coded. An experiment correcting the person who
built the mechanism is itself evidence this isn't scripted toward a foregone conclusion; if it
were, it would have confirmed what I expected.

**A genuine tipping point falls out of a smooth rule, with no threshold constant anywhere**
(`tests/test_sensitivity.py::test_business_failures_shows_a_real_threshold_around_drought_severity_0_4`,
`life100/simulation/sensitivity.py`): sweep drought severity from 0.05 to 0.50 (10 branches from
the identical starting state, 15 days each) and measure `business_failures`. Nothing in
`economy.py` mentions a "tipping severity" — a business only lays off/fails once its cumulative
`cash` crosses zero, and `cash` is driven by a purely linear function of severity
(`demand_multiplier`/`cost_multiplier`). Swept for real, the result is not linear at the
aggregate level:

| Severity | 0.05–0.30 | 0.35 | 0.40 | **0.45** | 0.50 |
|---|---|---|---|---|---|
| business_failures | 0 | 0 | 0 | **2** | 3 |

The sweep's own slope-ratio detector (a step's |slope| must be ≥3× the median of every other
step — see `sensitivity.py`'s methodology docstring for the exact test) independently locates the
jump between severity 0.40–0.45, then a refinement pass narrows it to **0.433–0.442**, all without
being told where to look. `health_incidents` and `avg_household_wealth` show the same located
jump (a real, correlated consequence, not a coincidence); `unemployment_rate` and
`avg_household_stress` are reported as having **no detected tipping point** in this range — a
smooth, gradual response — because they genuinely are smooth, not because the detector was tuned
to always find something. That "no tipping point" verdict for two of the six swept metrics is
itself part of the proof: a manufactured finding would have flagged all six.

---

## 3. The system can be experimentally used to compare possible futures

(`test_a_policy_intervention_produces_a_measurable_and_explainable_divergence`): branch a
70-citizen population mid-drought into two identical timelines. Apply exactly one difference — a
50% food subsidy — to one of them. Run both 20 more ticks under otherwise identical rules.

Real numbers from that run:

| Metric | Subsidized | Unsubsidized |
|---|---|---|
| Average household stress | **0.9686** | **0.9986** |
| Average wealth | 21,489.75 | 21,481.20 |
| Unemployment rate | 4.44% | 4.44% |
| Population / businesses | 73 / 34 | 73 / 34 |

The subsidy measurably eased stress relative to doing nothing, from the same starting point,
under the same disaster. The two timelines also produced **1,196 vs. 1,200 events that only
happened in one of them** — divergence isn't a hand-wave, it's countable, and every one of those
events is individually inspectable via `GET /events/{id}/causes`/`effects`. Critically, the
comparison isn't just "two different random runs": the actual `POLICY_CHANGED` event that caused
the split is a real, findable event in the subsidized timeline's own log, and shows up in its
list of divergent events — the tool traces the comparison back to the actual choice that was
made, not just to different numbers.

---

## Reproduce this yourself

```bash
uv run pytest tests/test_emergence.py -v
```

7 tests, ~11 seconds, no external infra required. Or drive it live through the running stack —
`POST /simulation/branch`, apply different interventions to each, `GET /simulation/compare` — see
`README.md`'s demo walkthrough.
