# Progress Log

Newest entries at the top. Each entry: date, SRS stage/section, what was done, what's next.

---

## 2026-08-22 — Full SRS build-out (post-submission), verified live end-to-end

**Context:** After the certificate submission slice was working, the user asked to build out
"everything mentioned in the SRS." This entry covers that full pass. See `SCOPE.md` for the
up-to-date gap analysis (what's still simplified/missing) — most of what it originally listed as
cut has since been implemented.

**Done, roughly in build order:**
1. **Entity depth** (SRS §6.1/6.2/6.5/6.7): full Citizen field set (financial/health/behavioral/
   goals), Household (property/assets/goals/living_conditions), new `Government` and `Resources`
   entities.
2. **Social relationships** (§12): family/coworker/neighbor/friend graph + real home-building
   assignment (a real gap found: households never had a home before this).
3. **Decision engine** (§10-11): deterministic (not LLM) daily decisions — purchase, school,
   job search, healthcare, loans, socializing.
4. **Life events** (§6.3): birth, death, marriage (with household merge), divorce (with household
   split) — the last four event types that were defined since day 1 but never emitted.
5. **Full disaster system** (§26): flood, earthquake, disease outbreak, economic recession, food
   shortage, energy crisis, generalized via `broad_cost_shock`/`broad_demand_shock` multipliers.
   Two real rule-4 violations caught and fixed here (disasters mutating state directly instead of
   through an event handler).
6. **Business Agent + Household Decision Agent** (§20.2-20.3): the last two of the four spec'd AI
   agents, completing the agent roster.
7. **Explainability/causality/memory** (§22-25): explicit `caused_by` links (never inferred),
   `GET /events/{id}/causes|effects`, curated per-citizen memories. Found and fixed a real bug:
   `CITIZEN_DIED` needed to snapshot family ties at time of death, since the engine clears a
   widow(er)'s live `spouse_id` right after.
8. **Alternate history** (§27-29): `branch_simulation()` (deep-copy based), `compare_simulations()`,
   reusing the causal-chain endpoints for butterfly-effect tracing instead of building a second
   mechanism. `AppState` generalized to a multi-simulation registry (backward-compatible property).
9. **Dashboard depth + businesses endpoint** (§30-32): 7-tab Streamlit UI covering every SRS §30
   view; added the missing `GET /businesses`.
10. **Observability + reproducibility** (§33, §35-36): `/observability/metrics`,
    `/simulation/reproducibility`.
11. **Real Snowflake** (§18-19): `warehouse/snowflake_pipeline.py`, using the user's own
    ACCOUNTADMIN credentials — creates the warehouse/database/schema on first use (XSMALL,
    auto-suspend 60s) and **verified live**: loaded 2500+ real events from Postgres into the
    user's actual Snowflake account via `POST /warehouse/build-snowflake`. Kept alongside (not
    replacing) the DuckDB path, which stays the default/test-covered one.

**Two real calibration/scale findings from a full live rebuild+replay** (world had drifted since
the certificate-submission verification, given how much new tick-loop logic landed):
- Confirmed the drought → cascade mechanism still produces a believable partial effect at full
  depth: 30 ticks with 100+ citizens now generates ~2500 events across purchases, school
  attendance, socializing, healthcare, job dynamics, resource extraction, marriages, and births —
  a genuinely rich historical dataset, not just the original narrow drought/layoff slice.
- Verified two branches with different Government-Agent-driven interventions (food subsidy vs.
  none) produce measurably different household stress after 15 ticks (0.9244 vs. 0.9572) — the
  counterfactual/timeline-comparison machinery works end-to-end with a real, not scripted,
  divergence.

**62/62 tests passing** (`uv run pytest`). Full docker-compose stack (5/5 containers) rebuilt and
re-verified live end-to-end after all of the above.

**Next:** see `SCOPE.md`'s gap table — Postgres schema depth, Alembic/k8s/secrets, a literal
World View map render, business resurrection after failure, and hourly (vs. daily) tick
granularity are the remaining known simplifications, in roughly that priority order if picked
back up.

---

## 2026-08-22 — Full stack complete and verified live (submission scope)

**Done, on top of the entry below:**
- Postgres models/CRUD + Kafka consumer worker (`db/`, `streaming/consumer.py`).
- DuckDB warehouse pipeline (`warehouse/duckdb_pipeline.py`) — fact_events/dim_citizen/dim_date.
- Government + Historian Gemini agents + validator (`agents/`), with mocked-LLM tests (never hit
  the live API during `pytest`).
- Full FastAPI app (`api/`) — simulation lifecycle, citizens, events/timeline, disasters, AI
  agents, warehouse endpoints. 27/27 tests passing.
- Dockerfiles (api/worker/dashboard) + `docker-compose.yml`, and a thin Streamlit dashboard.
- **Two real calibration bugs found and fixed via live `docker compose` testing** (not caught by
  unit tests, which used small populations/short runs): (1) default world grid produced ~5x too
  many businesses for the population; (2) citizen salaries were charged as a full day's expense
  every tick instead of a monthly figure divided down, making every business insolvent from
  tick 1 regardless of the drought. See `WORKING_NOTES.md` for the full detail.
- **Verified live, end-to-end, with a clean volume reset for reproducibility:** 5/5 containers
  healthy; drought → 20 ticks → 22 real JOB_LOST + 5 BUSINESS_FAILED events; Government and
  Historian agents both tested against the *real* Gemini API (not mocked) and behaved correctly
  (grounded citation, validated policy proposal); DuckDB warehouse built from Postgres.
- `README.md` written with the actual reproduced demo walkthrough (citizen `cit_0065`, Raj
  Shrestha, losing his job at tick 12 — a real, deterministic result of this seed, not scripted).
- Gemini model name corrected (`gemini-2.0-flash` → `gemini-3.6-flash`) after live API rejection.

**Next:** final read-through of all docs for internal consistency before submission (due
2026-08-24); optionally wire up real Snowflake if there's time left (credentials are in `.env`,
warehouse/database/schema not yet provisioned — see `SCOPE.md`). **[Done in the entry above.]**

---

## 2026-08-22 — Core simulation vertical slice (submission scope)

**Context:** Building a 2-day vertical slice for a SIEP certificate submission (due 2026-08-24),
not the full 30-milestone roadmap. See `SCOPE.md` for exactly what's in/out of scope, and
`WORKING_NOTES.md` for the live task checklist.

**Stage:** SRS §7 (World), §6 (Citizens/Households/Business), §13 (Economy), §14-16
(Events/streaming groundwork), ROADMAP Steps 1-17 condensed.

**Done:**
- Repo scaffolded: `git init`, planning docs moved to repo root, `pyproject.toml` (uv-managed,
  `uv sync` succeeds), `.env.example`, `.gitignore`.
- `CLAUDE.md`/`ROADMAP.md` updated: runtime AI provider switched from Anthropic/Claude to Google
  Gemini (Flash, free tier) — see `SCOPE.md` for why.
- `life100/simulation/world.py` — deterministic `generate_world(seed)`: zone grid + civic
  infrastructure (homes, school, hospital, bank, government, shops, factories).
- `life100/simulation/households.py` — `generate_population(seed, n=100)`: coherent
  citizens+households generated together (ages/relationships stay consistent).
- `life100/simulation/business.py` — `generate_businesses(seed, world, citizens)`: hires
  working-age citizens, guarantees at least one `food_production` and one `food_retail` business
  so the drought cascade always has a real chain to travel through.
- `life100/events/schemas.py` — `Event` (pydantic, frozen) with all SRS §14 required fields;
  `EventType` enum covers the full SRS §15 list plus `PRICE_CHANGED` (needed for cascade
  granularity, noted as an intentional schema extension per CLAUDE.md rule 5).
- `life100/events/producer.py` — `EventProducer` protocol; `InMemoryEventProducer` (default,
  used by all tests, no I/O); `KafkaEventProducer` (lazy-imports `confluent_kafka`, never raises
  out of `send()` — a broker outage degrades gracefully, never blocks the sim, SRS §16).
- `life100/events/store.py` — `EventLog`, the engine's in-process append-only source of truth
  and the Historian agent's future evidence source.
- `life100/simulation/engine.py` — `SimulationEngine.emit()` is the *only* path to a state
  change (CLAUDE.md rule 4): it builds the event, logs it, publishes it, then runs the matching
  handler. No other code touches a Citizen/Household/Business field directly.
- `life100/simulation/economy.py` + `disasters.py` — per-tick economic loop (food price →
  business cost/demand → household budget) and `trigger_drought()`. The cascade is computed, not
  scripted (SRS §3.3): `test_drought_cascades_into_job_losses_not_scripted` runs 15 ticks and
  asserts real `JOB_LOST` events emerge with citizens actually left unemployed in engine state.
- **17/17 tests passing** (`uv run pytest`): world determinism, population determinism/coherence,
  business hiring, event schema/log behavior, and the full drought→layoff cascade (plus a
  food-subsidy-policy dampening test, foreshadowing the Government Agent's proposal).

**Next:**
- Postgres models (`life100/db/models.py`) + `session.py` — citizens/households/businesses/events/
  simulation_state tables. **[Done]**
- `docker-compose.yml` bringing up Postgres + Redpanda; `life100/streaming/consumer.py` — a Kafka
  consumer that idempotently upserts events into Postgres. **[Done]**
- Then Day 2: DuckDB warehouse pipeline, Government + Historian Gemini agents + validator, FastAPI
  app, Dockerfiles, thin Streamlit dashboard, README/demo script. **[Done]**
- **Assumption to confirm later:** 1 tick = 1 simulated day for this submission (SRS's own "1
  tick = 1 hour" granularity is simplified — see `SCOPE.md`). **[Still the case — see SCOPE.md]**

## 2026-08-22 — The "What If?" Engine (experimentally comparable futures)

Direct response to the reframing: the project must let you actually run a controlled experiment
on the society, not just narrate that it could.

- `life100/simulation/experiments.py` (new) — `Scenario` dataclass + `run_experiment()`: branches
  the live simulation into a Control plus N scenario worlds via `branch_simulation`, runs each for
  an identical number of ticks, returns real `pct_change_vs_control` metrics and the actual engine
  objects (registered into `state.simulations` via the new `/experiments/run` router).
- `life100/simulation/disasters.py` — `trigger_drought()` gained a `severity` parameter (shock
  size + price ramp rate both now scale with it, previously hardcoded); new
  `trigger_emergency_employment_program()` reuses the existing `broad_demand_shock` mechanism
  with a negative magnitude rather than scripting a hiring event.
- `life100/simulation/decisions.py` — `government.healthcare_spending` wired into
  `_decide_healthcare()` as a real lever (access chance + cost), closing a gap where it was stored
  but never read; `agents/government.py`/`agents/validator.py` extended to match.
- Dashboard: new "What If? Lab" tab (disaster/severity/duration + Government intervention +
  Emergency Employment sliders, comparison table, grouped bar chart). Live-tested end to end;
  found and fixed a shared-y-axis chart bug (`resolve_scale(y="independent")`) where 0–1-scale
  metrics visually flatlined next to 100s-scale ones.
- **77 passed, 2 skipped** (`uv run pytest -q`) after this phase, including
  `tests/test_experiments.py`'s `test_one_city_three_futures_produces_real_measured_divergence`.
- Verified live via the actual dashboard (not just pytest): one branch point, three interventions,
  real divergent numbers each run — e.g. one run had Food Subsidy beat Emergency Employment on
  unemployment but lose on business failures; a later run at a different branch point had
  Emergency Employment sweep every metric instead. See `SCOPE.md` for the full write-up.

## 2026-08-22 (same day, later) — Sensitivity Analysis: find the tipping point

Direct response to "of everything, sensitivity-analysis tipping points is the one I'd prioritize."

- `life100/simulation/sensitivity.py` (new) — `run_sensitivity_sweep()`: sweeps `drought_severity`,
  branching the live simulation once per value, and detects a tipping point per metric via a
  disclosed slope-ratio test (a step's |slope| must be the sweep's max AND ≥3x the median of every
  other step), with an automatic refinement pass narrowing any bracket found. A metric with no
  qualifying step is reported as having no tipping point — never forced.
- New `POST /experiments/sensitivity` endpoint (`life100/api/routers/sensitivity.py`) and a
  "Sensitivity Analysis" section in the dashboard's What If? Lab tab: severity range + step count
  + duration sliders, per-metric line charts with the detected bracket shaded in red, or an honest
  "no tipping point — response is smooth" note.
- Fixed a real integration bug found only by testing the full sequence end to end: sweeping
  `drought_severity` from an already-mid-drought active simulation (e.g. right after running a
  What If Lab experiment) raised `"A drought is already active"`, since each swept branch tried to
  trigger a second drought on top of one inherited from the base state. Fixed with
  `_end_disaster_if_active()`, which ends the branch's copy of that disaster via a real
  `DISASTER_ENDED` event (CLAUDE.md rule 4: still only through the event system) before applying
  the swept severity — safe because each branch is a disposable copy.
- **Genuine, empirically-discovered finding** (not decided in advance): at `ticks=15`,
  `business_failures` is exactly 0 for every severity 0.05–0.30, then real businesses start
  failing above ~0.40 (refined to severity 0.433–0.442). The mechanism was already in the code —
  `economy._update_businesses` lays off/fails a business only once cumulative `cash` crosses
  zero, a hard per-business threshold sitting on top of a smooth, linear function of severity —
  nothing was added to manufacture this result. `unemployment_rate`/`avg_household_stress` swept
  over the same range show no detected tipping point (genuinely smooth), reported as such. Also
  found empirically: `ticks=30` (the What If Lab's default) saturates `food_price_index` and
  `avg_household_stress` at their caps for every severity, hiding this differentiation entirely —
  which is why the sensitivity sweep defaults to `ticks=15` instead. Full write-up with the actual
  numbers: `PROOF.md` §2, `SCOPE.md`.
- **84 passed, 2 skipped** (`uv run pytest -q`) after this phase, including the new
  `tests/test_sensitivity.py` (9 tests: determinism, input validation, the "no tipping point"
  case, a synthetic step-detection case, the real business_failures finding, and the 30-tick
  saturation finding) plus a `/experiments/sensitivity` end-to-end test in `test_api.py`.
- Verified live against the real Docker stack (not just pytest): `POST /experiments/sensitivity`
  through the containerized API reproduced the identical tipping-point bracket, and the dashboard
  section renders the shaded-band charts and honest "no tipping point" captions correctly.

## 2026-08-22 (same day, later still) — UI redesign: make the science impossible to miss

Direct response to explicit feedback that the engineering was stronger than the interface
communicated ("if a judge sees these screens first, they won't immediately perceive that").

- `/simulation/status` extended with `unemployment_rate`, `active_businesses`,
  `health_incidents`, `active_disasters_detail` (per-disaster magnitude) — one server-computed
  source for the new persistent status bar instead of each tab re-deriving its own numbers.
- New `render_status_bar()`: a single-line civilization status strip (day, population, food
  price, unemployment, businesses, health incidents, active disaster + severity), rendered once
  above the tabs so it's visible no matter which tab is open — the "still looking at the same
  living world" continuity the feedback specifically called out as missing.
- What If? Lab rebuilt around the result: controls collapsed into a `⚙ Configure experiment`
  expander (collapsed by default once a result exists), results shown as `EXPERIMENT #N` +
  per-world metric cards with real vs.-control deltas (`st.metric`, auto-colored), the old table/
  chart kept as supporting detail underneath rather than the headline.
- Sensitivity Analysis promoted out of What If? Lab into its own tab ("Where does the city
  break?") with a computed headline verdict ("Tipping point found in X, Y — N of 6 swept metrics
  show a genuine break" or an honest "No tipping point found anywhere in this range").
- World View gained a real causal drill-down: "Why is this business failing?" — pick a failed
  business, see its actual causal chain (root cause → ... → failure) rendered as a vertical arrow
  diagram (`render_causal_chain()`, shared with Events & Causality), plus a real count of layoff
  events/affected employees. Nothing here is invented — it walks the same `trace_causes` data
  already used elsewhere.
- Events & Causality's trace tool now shows that same arrow-chain diagram plus a real "N direct
  effects touching M entities" summary, instead of two bare side-by-side dataframes.
- AI Agents given a light "Decision Room" framing (explicitly NOT a full rebuild, per the
  feedback's own prioritization): one-line pipeline explanation + a compact live status recap +
  each panel stating what it currently sees before proposing.
- Added a second tagline — "A civilization small enough to understand. Complex enough to surprise
  you." — under the existing "Only 100 people. Every life matters," per explicit feedback to keep
  the original and lean into it rather than replace it.
- Deliberately no decoration/gradient/neon restyle — same dark theme throughout; every change is
  information hierarchy, matching the feedback's explicit "less decoration, more information
  hierarchy... don't build a prettier dashboard."
- **84 passed, 2 skipped** (`uv run pytest -q`) — `tests/test_api.py` extended with assertions on
  the new status fields.
- Verified live against the real Docker stack for every changed screen: status bar renders on
  World View/What If Lab/Sensitivity Analysis; the World View causal drill-down correctly found
  `biz_001`'s real failure chain (`Disaster Started → Job Lost`, "6 layoff event(s)... affecting 6
  employee(s)"); the What If Lab hero cards rendered real deltas per world; the Sensitivity tab's
  headline verdict correctly reported a genuinely different tipping point
  (`unemployment_rate`, severity 0.292–0.300) on a different branch state than the earlier
  business_failures finding — reinforcing it's a live computation, not a cached result.

## 2026-08-22 (same day, later still) — typography/chart refinement: no emoji, no neon

Explicit follow-up after the redesign above: user was asked to choose between a bold "sci-fi HUD"
direction and staying understated; chose the latter explicitly, plus "no emojis."

- Removed every emoji from the dashboard (status bar, buttons, expanders, headings) — replaced
  with plain uppercase text labels (e.g. `DAY`/`POP`/`FOOD`/`UNEMPLOYMENT` instead of pictograms).
- Registered one shared Altair theme (`life100_dark`): monospace axis/legend/title fonts, muted
  gridlines, and a single deliberate 6-color palette (`LF100_RED/BLUE/VIOLET/GREEN/AMBER/TEAL`)
  now reused as the default categorical scale across every chart in every tab, replacing what had
  been a different ad hoc hex color hand-picked per chart.
- Sensitivity Analysis's tipping-point verdict and the causal-chain boxes (World View, Events &
  Causality) now use a colored left-border accent (CSS class) instead of a warning/arrow emoji —
  same "this matters" signal via color/typography, not an icon.
- Global light-touch CSS on `st.metric` widgets: monospace tabular-number values, small-caps
  uppercase labels, applied once, affecting What If Lab's hero cards and City Dashboard.
- Found and fixed a real bug during this pass: an f-string CSS block had one un-escaped brace
  pair (`.lf100-seg { white-space: nowrap; }` inside an f-string) which `ast.parse`/`py_compile`
  did NOT catch (it's syntactically valid Python — `white - space` parses as subtraction of two
  undefined names) but would have raised `NameError` at runtime the first time the page rendered.
  Caught by manually executing the exact snippet in isolation before deploying, not just
  syntax-checking — a reminder that f-string brace bugs can pass static checks and still crash at
  runtime.
- **84 passed, 2 skipped** (`uv run pytest -q`) — no test changes needed, this was UI-only.
- Verified live end to end: status bar renders correctly with all 6 segments and no emoji; What
  If Lab's hero cards show monospace values + the new muted palette in the comparison chart;
  Sensitivity Analysis's verdict renders as a clean bordered box, not an emoji heading.

## 2026-08-22 (same day, later still) — the full "living instrument" UI redesign

Direct response to a 19-point redesign brief: the dashboard must read as "I can intervene in this
city, observe what happens, and investigate why" — not "a Streamlit app with nine tabs."

- **Four-mode IA**: `CITY` (World/Overview/Economy/Health), `EXPERIMENT` (What If?/Find the
  Breaking Point/Alternate Histories), `INVESTIGATE` (Why Did This Happen?/Decision Room),
  `PEOPLE` (Citizens/Households/Businesses) — nested `st.tabs`, replacing the old flat 10-tab list.
- **Landing gate** ("Enter the City" / "Run Guided Demo") replacing the old always-visible
  sidebar-control wall; sidebar reduced to a collapsed "Advanced Controls" expander.
- **Primary time controls moved into CITY > Overview**: `+1 Day`/`+5 Days`/`+30 Days` buttons plus
  a live "what just happened" event feed built from the real events that specific advance produced
  (verified live: real `Job Lost`/`Business Failed`/`Price Changed` rows appeared after a real
  30-day advance).
- **Real map click-to-panel**: `pydeck_chart(..., on_select="rerun", selection_mode="single-object")`
  — clicking a building opens a context card with its real business cash/employees/status or
  household stress, plus a "Why?" button reusing the existing causal-chain trace. Verified live:
  clicking a factory correctly opened `bld_0091 / Food Production / Cash 3692.71 / Employees 5 /
  STABLE`.
- **Per-citizen "Explain my story"** (PEOPLE > Citizens): calls the Historian agent, shows a real
  evidence-grounded indicator instead of a fabricated confidence score. Verified live including the
  honest zero-history case.
- **Real timeline visualization** for Alternate Histories: `/simulation/list` extended to expose
  each branch's already-recorded `parent_simulation_id`/`branch_point_tick` (`branch_info` existed
  on the engine but was never surfaced by the API); rendered as an Altair bar+fork-tick chart.
- **A scripted-presentation, unscripted-simulation Guided Demo**: 8-step linear walkthrough (Day 0
  → drought → real price rise → real business pressure → a real citizen's real Historian-explained
  story → a real 3-world experiment → a real sensitivity sweep → a discovery screen using whatever
  the sweep actually found). Only narration pacing is pre-written; every number is a live API call
  made at that step. Verified live end to end, including the honest "no tipping point was found"
  fallback ending.
- **Real bug found and fixed**: running `/experiments/run` from a simulation with an already-active
  disaster failed with "A drought is already active" and failed *silently* in the dashboard (no
  error shown) — each scenario branch inherits the base state's active disasters. Fixed identically
  to the existing `sensitivity.py` fix (end the branch's own copy via a real `DISASTER_ENDED`
  event first). Added `test_running_an_experiment_from_a_simulation_already_mid_disaster_does_not_raise`
  plus error surfacing in the dashboard so this class of failure is never silent again.
- **Known, disclosed limitation**: the Sensitivity tab's chart-click "Why?" drill-down did not
  reliably register the click selection in live testing (Altair `selection_point`/`on_select`) —
  everything else on that tab works correctly; this one embellishment is a harmless no-op, not
  removed, documented rather than hidden.
- **85 passed, 2 skipped** (`uv run pytest -q`).
- Verified live via a full Docker rebuild, covering every new feature: landing screen, 4-mode nav,
  map click-to-panel, Overview's day-stepper + event feed, Alternate Histories branch metadata,
  Citizens' Explain My Story, and the complete 8-step Guided Demo through to its discovery screen.

## 2026-08-22 (same day, later still) — a real bug found via deliberate investigation, then fixed

Asked directly to run genuinely exploratory tests against the live simulation and find something
real — not a manufactured or flattering result.

- **Multi-seed robustness check**: reran the drought/business_failures sensitivity sweep at 10
  independent seeds. All 10 show a tipping point, clustering tightly at severity 0.445 ± 0.033 —
  strong evidence the original PROOF.md finding (found at one seed) is a real property of the
  economy's cash-flow arithmetic, not a coincidence.
- **Cross-disaster sweep**: swept all six non-drought disasters' own tunable magnitude parameters
  at the same 15-tick window. Zero business failures from any of them — only drought produces this
  effect in a realistic timeframe. Chasing why led to a real discovery: earthquake's (and flood's)
  "structural collapse" business-failure path was checked against `cash <= 0`, but damage is a
  *percentage of current cash* — `cash * (1 - damage_fraction)` can only equal exactly zero at
  `damage_fraction == 1.0`. Verified directly: a 99% hit left a business with 18.31 cash, fully
  active. The one unit test covering this (`test_earthquake_can_fail_businesses_outright`)
  happened to hardcode the only value that ever worked, and `/disasters/earthquake` didn't even
  expose `damage_fraction` to real callers — a documented, tested feature that was unreachable
  through any actual use of the system.
- **Fixed**: `engine.py`'s `_apply_business_contracted` now triggers structural-collapse failure
  when remaining cash can't cover the business's own tracked `expenses` (a real insolvency
  condition tied to an already-computed quantity, not an arbitrary constant), falling back to the
  exact-zero check when expenses hasn't been computed yet. `/disasters/earthquake` and
  `/disasters/flood` now accept `damage_fraction`/`affected_share` so the fix is actually reachable
  through the API, not just direct Python calls.
- Verified the fix does the intended thing, not an overcorrection: a healthy business (cash 4205.50,
  expenses 986.22) survives a severe 0.7 earthquake with cash to spare (1261.65); a business already
  weakened by a drought (cash 1885.22, expenses 1089.25) genuinely fails under the same 0.7
  earthquake (cash lands at 565.57 — positive, but below what it needs to operate).
- New regression test: `tests/test_disasters.py::test_a_realistic_damage_fraction_can_also_fail_an_already_weakened_business`,
  plus an API-level test confirming both endpoints accept the new parameters.
- **87 passed, 2 skipped** (`uv run pytest -q`).
- Full write-up with all real numbers in `PROOF.md` §2.
