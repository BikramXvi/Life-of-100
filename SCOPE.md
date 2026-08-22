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
- **Dashboard** (§30-32): World View (a real rendered zone/building grid, not just tables), City
  Dashboard, Citizens (+ memories + relationships + timeline), Households, Businesses, Events &
  Causality (with a trace lookup), all four AI agents, Alternate Timelines (branch/compare/
  activate) — all as thin calls to the FastAPI layer.
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

## Explicitly out of scope (matches SRS §45's own list, not a cut)

Multiple cities, inter-city trade, political elections, cultural evolution, reinforcement
learning, fully LLM-controlled citizens, graph databases, PostGIS, Spark/Flink/Iceberg, Redis,
Kubernetes, distributed simulation — SRS §45 names these as future extensions beyond the current
project's own scope, not something this build cut short.
