# SCOPE.md — Implementation Status vs. SRS.md/ROADMAP.md

This document tracks how much of the full LIFE/100 vision (`SRS.md`, `ROADMAP.md`) is actually
implemented, and honestly documents what's still simplified or missing. It started as a
2-day certificate-submission scope cut; most of what was originally cut has since been built
back in (see `PROGRESS.md` for the full history). This is now closer to a running gap analysis
than a list of deliberate exclusions.

## Implemented and verified live (real Docker stack + real Gemini + real Snowflake)

- **World & population** (§6, §7): deterministic world/citizen/household/business generation,
  full SRS §6.1 citizen field set (identity/education/employment/financial/health/psychological/
  behavioral/goals), family ties (spouse/parent/child), households with property/assets/goals.
- **Social relationships** (§12): family/friend/coworker/neighbor graph, generated deterministically
  and updated by the decision engine's socializing.
- **Government & Resources entities** (§6.5, §6.7): structured policy levers, tracked food/raw-material
  stocks with `RESOURCE_EXTRACTED` events.
- **Daily decisions & life events** (§10, §11, §6.3): a deterministic (not LLM-driven, per §11's own
  rule) per-tick decision engine — purchases, school, job search, healthcare, loans, socializing —
  plus birth/death/marriage/divorce, all through real events.
- **Economy** (§13): tick-based price/cost/demand cascade, calibrated so a disaster produces a
  believable partial cascade (not instant total collapse, not nothing).
- **Full event architecture** (§14-15): all SRS-listed event types are emitted somewhere in the
  system, plus two documented schema extensions (`PRICE_CHANGED`, `HEALTH_IMPACTED`) with the same
  discipline CLAUDE.md rule 5 asks for.
- **Streaming, operational store, warehouse** (§16-19): Kafka-compatible Redpanda → consumer worker
  → Postgres, **and now real Snowflake** (see below) alongside a DuckDB stand-in.
- **All four AI agents + safety boundary** (§20-21): Government, Historian, Business, Household
  Decision — every one follows propose → validate → (accept → apply | reject), each step its own
  event, running on Gemini Flash (see the AI-provider note below).
- **Explainability, causal chains, memory** (§22-25): `caused_by` links recorded at emission time
  (never inferred/fabricated), `GET /events/{id}/causes|effects`, curated per-citizen memories.
- **Full disaster system** (§26): drought, food shortage, flood, earthquake, disease outbreak,
  economic recession, energy crisis — each a real shock with emergent downstream effects.
- **Counterfactual branching, timeline comparison, butterfly-effect tracing** (§27-29): deep-copy
  branching, per-branch metrics, divergent-event lists, reusing the causal-chain endpoints for
  butterfly-effect tracing rather than a second mechanism.
- **Dashboard** (§30-32): World View is a real interactive 3D city render (pydeck/deck.gl) —
  rectangular extruded buildings (not lollipop columns) with per-kind footprint/height, PBR-ish
  material shading, a connected street network (not just colored road tiles), and homes tinted
  by a green→red gradient reflecting their household's *real* `financial_stress` (data, not
  decoration) — plus a deterministic per-building color/height jitter so the skyline reads as
  organic rather than a uniform grid. Drag to orbit, scroll to zoom, hover for details. Every
  other tab has real statistical charts (Altair) driving the data, not just raw
  tables/JSON: City Dashboard has time-series trend lines (food price, population, employment,
  event volume) reconstructed from the event log; Citizens has age/wealth histograms and an
  occupation breakdown; Households has a savings-vs-stress bubble chart; Businesses has an
  industry donut and a cash-on-hand bar chart; Events & Causality has event-type and volume
  breakdowns plus the causal trace lookup; Alternate Timelines renders the A/B comparison as
  grouped bars instead of a JSON dump. All as thin calls to the FastAPI layer.
- **Observability & reproducibility** (§33, §35-36): `/observability/metrics` (ticks/sec, CPU/mem,
  active counts), `/simulation/reproducibility` (seed, config, versions, agent config).

### Real Snowflake (§18-19) — implemented, not just planned
`warehouse/snowflake_pipeline.py` connects with the user's real credentials, creates the
warehouse/database/schema on first use if missing (`XSMALL`, `AUTO_SUSPEND=60s`, starts
suspended to minimize credit usage), and loads `fact_events`/`dim_citizen` from Postgres —
**verified live**: `POST /warehouse/build-snowflake` successfully loaded 2500+ real events into
the user's own Snowflake account. `POST /warehouse/build` (DuckDB) remains the default/primary
path since it needs no external account and is what the automated test suite can exercise
locally; Snowflake is the opt-in real-infrastructure path alongside it.

### Alembic migrations
`migrations/` (env.py wired to `DATABASE_URL` and `db/models.py`'s metadata) with a real initial
migration (`949daf9b6ae7_initial_schema.py`) generated against — and applied to — the live
Postgres, verified via `alembic upgrade head` inside the running API container.
`db/session.py`'s `create_all` is left in place too (idempotent, zero-friction for fresh local
dev) — going forward, a model change should get a matching `alembic revision --autogenerate`.

### AI provider: Gemini Flash, not Anthropic/Claude
The original `SRS.md`/`ROADMAP.md` specified the Anthropic API. Switched to Google Gemini
(`gemini-3.6-flash`) because that's the key the user had — see `CLAUDE.md`'s tech-stack section
and `ROADMAP.md` §4.7/§25 for where this was updated. The agent architecture (propose → validate →
apply) is identical regardless of provider; `agents/base.py` isolates the SDK call.

## Still simplified or not built

| Gap | Why | What it would take |
|---|---|---|
| Postgres schema depth | 9 tables now (citizens/households/businesses/events/simulation_state/relationships/government/infrastructure/agents) vs. SRS §17's full wishlist — missing dedicated `assets`/`debts`/`health_records`/`education` tables specifically | The event log is the real durable record and citizen fields already carry this data; splitting it into normalized tables is schema work, not new capability, at this point. |
| k8s, secret managers | Not needed to demonstrate the required capability | Docker Compose + `.env` is the pragmatic floor for this project's scale. |
| Full 1-tick-per-hour granularity | 1 tick = 1 simulated day (SRS §9 specifies hourly) | Would need a full daily-routine scheduler (wake/commute/work/lunch/shop/sleep as sub-tick phases) rather than one decision pass per day. |

## Fixed since the last pass

- **A failed business couldn't be resurrected** — `take_loan` on an inactive business added cash/debt
  but never flipped `active` back to `True`. Fixed: a loan that brings cash positive now reopens
  the business via a `BUSINESS_EXPANDED('reopened_after_loan')` event.
- **The Kafka→Postgres consumer's incremental state updates never actually ran** — a significant
  bug, found only by directly inspecting Postgres after live-testing (no unit test could have
  caught it, since the test suite doesn't run against a real broker/DB). Two independent causes,
  both fixed:
  1. `insert_event`'s duplicate check used `result.rowcount`, but psycopg3 reports
     `rowcount == -1` for `INSERT ... ON CONFLICT DO NOTHING` regardless of outcome — so every
     event looked like a duplicate and `apply_event_to_state` silently never ran. Fixed with a
     `RETURNING` clause, the reliable way to detect an actual insert.
  2. The consumer subscribed to topics that had never been produced to yet (e.g. `families`,
     since no household-level event had fired) — Redpanda left the whole consumer group unable
     to reach a stable partition assignment, so messages on topics that *did* exist were never
     processed either, with no error beyond a repeating `UNKNOWN_TOPIC_OR_PART` warning. Fixed by
     having the worker explicitly pre-create every topic via `AdminClient.create_topics()` before
     subscribing, rather than relying on implicit auto-create (which triggers on produce, not on
     a consumer's subscribe).

  Practical impact before the fix: `fact_events`/the event log itself was always correct (its
  INSERTs succeeded regardless of the buggy return-value check) — but `citizens`/`businesses`/
  `government`/`simulation_state` in Postgres never reflected anything past the initial bulk
  load. Verified after the fix: a 20-tick drought run now shows Postgres's `citizens` table
  correctly listing laid-off citizens as `unemployed`, and `simulation_state` exactly matching
  the live engine (tick 20, food_price_index 2.91, 1650/1650 events) — the "Postgres reflects
  current operational state" claim in `README.md`/`PROGRESS.md` is now actually true, not just
  documented as true.

## Added since the last pass: the "What If?" Engine

This is the direct answer to "the system must let you experimentally compare possible futures,"
not a new UI decoration:

- **`life100/simulation/experiments.py`** — `run_experiment(base_engine, scenarios, ticks)` takes
  the CURRENT live simulation, deep-copies it via `branch_simulation` once per scenario (plus one
  untouched control), applies each scenario's disaster/policy/stimulus, runs every branch for the
  same number of ticks, and returns real measured `pct_change_vs_control` numbers — never
  hand-written outcomes. All resulting engines are registered into `state.simulations` (a real bug
  caught and fixed before it shipped: the first version ran the branches but never made them
  reachable through the API).
- **`POST /experiments/run`** (`life100/api/routers/experiments.py`) and the dashboard's **"What
  If? Lab"** tab: pick a disaster + severity + duration, a Government intervention (food subsidy /
  interest rate / healthcare funding) for World B, and an Emergency Employment stimulus for World
  C, then run all three plus a no-disaster Control side by side with a real comparison table and
  independently-scaled bar charts (a `resolve_scale(y="independent")` fix was required — otherwise
  a 0–1-scale metric like `unemployment_rate` visually flatlined next to a 100s-scale metric like
  `health_incidents` in the same chart).
- **Verified live, not just unit-tested:** one branch point, three interventions, genuinely
  different and non-obvious results — Food Subsidy and Emergency Employment aren't simply
  "better/worse," they trade off differently across runs (one run: Food Subsidy beat Emergency
  Employment on unemployment but lost on business failures; a later run at a different branch
  point had Emergency Employment sweep every metric). That run-to-run variability is itself
  evidence the outcome isn't scripted — a scripted demo would print the same "moral" every time.
- **`trigger_drought()` gained a `severity` parameter** (previously a fixed `DROUGHT_INITIAL_SHOCK`)
  so the initial shock size — and now also the food-price ramp rate — actually varies with the
  slider, making a future sensitivity-analysis sweep (SCOPE.md's still-open "find the tipping
  point" item) possible without touching the economy model.
- **`government.healthcare_spending` was decorative until now** — stored on the `Government`
  dataclass and settable via the Government Agent's policy proposals, but no mechanic ever read
  it. `decisions.py`'s `_decide_healthcare()` now scales both access chance and out-of-pocket cost
  with funding level, so the What If Lab's "Healthcare funding" slider does something real; the
  agent-facing schema/validator (`agents/government.py`, `agents/validator.py`) were extended to
  match.
- **`trigger_emergency_employment_program()`** is a new disaster-module function but is not a
  disaster — it reuses the existing `broad_demand_shock` mechanism with a negative magnitude (a
  positive demand shock), so re-employment happens through the same hiring mechanics every other
  scenario uses, rather than a hand-scripted "everyone gets hired" event.

## Added since the last pass: Sensitivity Analysis (find the tipping point)

- **`life100/simulation/sensitivity.py`** (new) — `run_sensitivity_sweep()` branches the CURRENT
  simulation once per swept value of `drought_severity` (a real, independent run each time, not an
  interpolated guess), then flags a tipping point per metric only when a step's |slope| is both
  the sweep's maximum AND at least `TIPPING_RATIO=3.0`x the median |slope| of every other step —
  a disproportionate jump, not just the largest of several similar changes. A metric with no such
  step is reported as having no detected tipping point, never forced to show one. When a candidate
  IS found, a second, real refinement sweep re-samples inside that bracket to narrow it further.
- **`POST /experiments/sensitivity`** + a new "Sensitivity Analysis" section in the dashboard's
  What If? Lab tab: pick a severity range and step count, run the sweep, see the full
  severity-response curve per metric with the detected tipping-point bracket shaded, or an honest
  "no tipping point — response is smooth" caption when none was found.
- **A genuine, mechanistically-explainable finding, not a manufactured one:** at `ticks=15`,
  `business_failures` stays at exactly zero for every severity from 0.05–0.30, then real
  businesses start failing above ~0.40 (refined to 0.433–0.442). This isn't a hardcoded
  threshold — `economy._update_businesses` only lays off/fails a business once its cumulative
  `cash` crosses zero, a hard per-business condition sitting on top of a smooth, linear function
  of severity. `unemployment_rate` and `avg_household_stress`, swept over the same range, show
  **no** detected tipping point (a smooth response) — reported honestly as such, which is itself
  part of the evidence the detector isn't tuned to always find something. See `PROOF.md` §2 for
  the full write-up.
- **Why `ticks=15`, not 30:** empirically verified (`test_food_price_and_stress_saturate_at_the_default_30_tick_window`)
  that at 30 ticks both `food_price_index` and `avg_household_stress` saturate at their hard caps
  for every severity in the swept range, erasing the very differentiation the sweep exists to
  find — the same saturation issue documented earlier for the drought-severity unit test.

## Added since the last pass: a UI redesign around the science, not the forms

Direct response to explicit feedback: "the underlying system is much stronger than what these
screenshots communicate... don't build a prettier dashboard, build a UI that makes the science
impossible to miss." Concretely:

- **A persistent civilization status bar** (`render_status_bar()`), rendered once above the tabs
  so it stays visible no matter which tab is open: day, population, food price, unemployment,
  active businesses, health incidents, and any active disaster with its severity. Backed by a
  richer `/simulation/status` (now also returns `unemployment_rate`, `active_businesses`,
  `health_incidents`, `active_disasters_detail` with each disaster's magnitude) so this is one
  server-computed source of truth, not four tabs each re-deriving the same numbers.
- **What If? Lab redesigned around the result, not the controls**: the scenario/policy sliders
  now live in a collapsed-by-default `⚙ Configure experiment` expander; the result is a row of
  world "cards" (`st.metric` with real vs.-control deltas, colored red/green automatically) under
  an `EXPERIMENT #N` counter, with the comparison chart and full metrics table now supporting
  detail rather than the headline.
- **Sensitivity Analysis promoted to its own tab** ("Where does the city break?") instead of
  living under What If? Lab's controls — with a headline verdict line ("Tipping point found in
  X, Y — N of 6 swept metrics show a genuine break" / "No tipping point found anywhere in this
  range") computed from the real per-metric results, not just per-chart captions.
- **World View gained a real causal drill-down**: "Why is this business failing?" lets you pick
  any failed business and renders its actual causal chain (root cause → ... → failure) as a
  vertical arrow diagram, plus an honest count of real layoff events/affected employees — reusing
  the existing `trace_causes` endpoint, never inventing a step.
- **Events & Causality's trace tool** now renders the same arrow-chain visual (root cause first)
  alongside a real "N direct downstream effects, touching M entities" summary, instead of two
  bare dataframes side by side.
- **AI Agents given a light "Decision Room" framing** (not a full rebuild, per explicit
  deprioritization): a one-line pipeline explanation (propose → validate → accept/reject →
  apply) plus a compact live status recap, and each agent panel now states what it currently
  sees (food price, active disasters) before proposing — still functional-first, not restyled
  into a chatbot.
- **Branding leaned into harder**: added "A civilization small enough to understand. Complex
  enough to surprise you." under the existing "Only 100 people. Every life matters." tagline,
  per explicit feedback to keep the original and lean into the philosophy, not replace it.
- Deliberately did NOT add decoration, gradients, or a "flashy AI startup" restyle — the existing
  dark theme was kept as-is; every change here is information hierarchy (status bar, hero cards,
  causal diagrams), not visual polish for its own sake.

## Explicitly out of scope (matches SRS §45's own list, not a cut)

Multiple cities, inter-city trade, political elections, cultural evolution, reinforcement
learning, fully LLM-controlled citizens, graph databases, PostGIS, Spark/Flink/Iceberg, Redis,
Kubernetes, distributed simulation — SRS §45 names these as future extensions beyond the current
project's own scope, not something this build cut short.
