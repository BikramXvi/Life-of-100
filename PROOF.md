# PROOF.md — The three things that actually matter

Feature count doesn't make this project real. Three specific properties do:

1. **It isn't scripted.**
2. **Complex behavior emerges from simple rules.**
3. **The system can be experimentally used to understand and compare possible futures.**

Everything below is backed by a durable, re-runnable test in `tests/test_emergence.py` — not a
narrated claim. Run `uv run pytest tests/test_emergence.py -v` to verify all of it yourself. The
numbers quoted here are from actual runs against `seed=847291`, reproduced while writing this
document.

**Regenerated 2026-08-23** after the SRS §9 hourly-tick change (see `SCOPE.md`/`PROGRESS.md`) —
every number below is a fresh live run against the current hourly engine, not left over from
before. Some numbers came back byte-identical to the pre-change run (the sensitivity sweep, the
10-seed robustness tables, the drought-weakened-business earthquake example) because those
scenarios only exercise `economy.py`'s daily cadence, which the hourly-tick change deliberately
left unchanged. Others shifted slightly (the contagion count, the wealth-dispersion table, the
policy-intervention comparison) because those depend on `decisions.py`'s citizen-level RNG, which
necessarily changed when decisions were spread across specific hours of the day instead of one
daily batch — the *mechanism and magnitude* are the same, the *exact* numbers moved by noise.

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
different seeds, same drought, same day count. The *specific* citizens who lose their jobs are
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
drought raises through everyone's higher cost of living. Running a 60-day drought for 90 total
days produces **16 layoffs at non-food businesses** (manufacturing, retail) that were never the
disaster's target. This is contagion through one shared variable, not two rules bolted together.

It gets more interesting: those 16 layoffs happen on days 65–90, well *after* the drought's
official 60-day "active" window ends at day 60. The effect **outlives the disaster**, because
household stress decays slowly. Writing the explainability check for this exposed a real gap —
the original `caused_by` logic only looked at *currently active* disasters, so these lagged,
second-order layoffs were showing up with **no recorded cause at all**. Fixed by having the
engine remember the most recent disaster's event even after it ends
(`engine.last_disaster_event_id`), and citing it whenever stress is still elevated enough to
plausibly be the reason. All 16 now correctly trace back to the real `DISASTER_STARTED` event —
verified, not assumed.

**A shock changes wealth dispersion — in the direction I didn't expect**
(`test_a_shock_measurably_changes_wealth_dispersion_from_identical_starting_conditions`): branch
the same population twice, apply a drought to only one branch, run both 60 days under otherwise
identical rules. I wrote this test expecting a shock to *widen* inequality — the naive
assumption. The actual measurement:

| Day | Treatment (drought) net-worth spread | Control net-worth spread | Difference |
|---|---|---|---|
| 10 | 16,115 | 16,137 | −22 |
| 20 | 16,014 | 16,092 | −78 |
| 30 | 15,852 | 16,006 | −154 |
| 40 | 15,714 | 15,923 | −209 |
| 50 | 15,522 | 15,819 | −297 |
| 60 | 15,351 | 15,720 | −369 |

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

**The tipping point is a property of the economy, not an accident of one seed**
(investigated live, not yet a permanent test — see below for why): the sweep above was run once,
at `seed=847291`. Repeating it independently at 10 different seeds (`847291, 111111, 222222,
333333, 444444, 555555, 666666, 777777, 888888, 999999`), same population, same severity range:

| | Result |
|---|---|
| Seeds showing a `business_failures` tipping point | **10 / 10** |
| Tipping-bracket midpoints | 0.396, 0.421, 0.429, 0.438, 0.446, 0.463, 0.463, 0.471, 0.471, 0.479 |
| Mean ± population stdev | **0.447 ± 0.025** |

Every one of ten completely different populations — different names, ages, savings, employer
assignments — breaks in the same narrow band (severity 0.42–0.48). That consistency is the real
signature of an emergent property of the cash-flow arithmetic, not a fluke of one specific city.

**Only drought produces this effect within a realistic window — and chasing why exposed a real
bug, now fixed.** Sweeping every other disaster's own tunable magnitude parameter (flood/
earthquake damage_fraction 0.1–0.9, disease/recession/energy magnitude 0.05–0.5) at the same
15-day window used above: **zero business failures from any of them.** Tracing why led to
`engine.py`'s `_apply_business_contracted` handler — earthquake's docstring promises "some
businesses may be damaged badly enough to fail outright," but damage was applied as a *percentage
of current cash* and failure required `cash <= 0` exactly. Since `cash * (1 - damage_fraction)`
is non-negative for any `damage_fraction <= 1.0`, only an exact **100.000% wipeout** could ever
zero out a business — verified directly:

| damage_fraction | Cash before | Cash after | Failed? |
|---|---|---|---|
| 0.99 (99% wiped out) | 3748.69 | 37.49 | No |
| 1.00 (100% wiped out) | 3748.69 | 0.00 | Yes |

And the API's `/disasters/earthquake` endpoint didn't even expose `damage_fraction` — every real
trigger used the hardcoded default of 0.7, which can never fail a business under the old check.
The *only* place `damage_fraction=1.0` ever appeared was one unit test that happened to hardcode
that exact edge value — a real, documented, tested feature that was unreachable through any actual
use of the system, hidden precisely because the one test covering it used the only value that
works. **Fixed**: failure now triggers when a business can't cover even one more round of its own
tracked `expenses` (a real insolvency condition, not the impossible cash-exactly-zero edge case),
and the API now exposes `damage_fraction`/`affected_share` for both flood and earthquake. Verified
the fix does the intended thing — a healthy business survives a severe hit, a business already
weakened by a drought does not:

| Scenario | Cash before | Cash after | Failed? |
|---|---|---|---|
| Healthy business, earthquake damage_fraction=0.7 | 5677.98 | 1703.39 | No (cash still covers expenses) |
| Drought-weakened business, same 0.7 earthquake | 1885.22 | 565.57 | **Yes** (positive cash, but below its own expenses) |

`tests/test_disasters.py::test_a_realistic_damage_fraction_can_also_fail_an_already_weakened_business`
locks this in as a regression test.

**Follow-up robustness check, and an honest side-finding.** Re-ran the same 10-seed sweep for
`disease_outbreak` and `economic_recession`'s own `demand_magnitude`, watching `unemployment_rate`
this time (the metric each of them actually breaks, per the original single-seed sweep):

| Disaster | Seeds with a tipping point | Mean bracket midpoint | Stdev |
|---|---|---|---|
| `disease_outbreak` | 9 / 10 | 0.469 | 0.016 |
| `economic_recession` | 9 / 10 | 0.469 | 0.016 |

Both cluster even tighter than drought's. But the two disasters' *entire* per-seed result series
came out byte-identical — worth checking rather than reporting two tables and moving on.
`trigger_economic_recession` turns out to be exactly `_start_disaster(kind="broad_demand_shock",
magnitude=demand_magnitude)` — mechanically identical to `disease_outbreak`'s demand-shock
component. `disease_outbreak` additionally emits a direct `HEALTH_IMPACTED` event to ~35% of
citizens, which the identical results show has **no measurable effect on unemployment within this
15-day window** — the entire employment effect comes from the shared demand-shock mechanism, not
from the disease's own distinguishing feature. Not a bug: a citizen's health hit raises stress,
and stress feeds into `demand_multiplier` (the same channel drought uses) — but that's a slower,
indirect path that plausibly needs longer than 15 days to show up, unlike the immediate shock. A
genuinely disclosed observation, not a manufactured "both diseases matter equally" conclusion.

---

## 3. The system can be experimentally used to compare possible futures

(`test_a_policy_intervention_produces_a_measurable_and_explainable_divergence`): branch a
70-citizen population mid-drought into two identical timelines. Apply exactly one difference — a
50% food subsidy — to one of them. Run both 20 more days under otherwise identical rules.

Real numbers from that run:

| Metric | Subsidized | Unsubsidized |
|---|---|---|
| Average household stress | **0.9693** | **0.9986** |
| Average wealth | 21,497.46 | 21,493.46 |
| Unemployment rate | 6.67% | 6.67% |
| Population / businesses | 73 / 34 | 73 / 34 |

The subsidy measurably eased stress relative to doing nothing, from the same starting point,
under the same disaster. The two timelines also produced **1,243 vs. 1,246 events that only
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

6 tests, under a second, no external infra required. Or drive it live through the running stack —
`POST /simulation/branch`, apply different interventions to each, `GET /simulation/compare` — see
`README.md`'s demo walkthrough.
