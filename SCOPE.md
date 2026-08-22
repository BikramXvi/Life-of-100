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
- **Dashboard** (§30-32): City Dashboard, Citizens (+ memories + relationships + timeline),
  Households, Businesses, Events & Causality (with a trace lookup), all four AI agents, Alternate
  Timelines (branch/compare/activate) — all as thin calls to the FastAPI layer.
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

### AI provider: Gemini Flash, not Anthropic/Claude
The original `SRS.md`/`ROADMAP.md` specified the Anthropic API. Switched to Google Gemini
(`gemini-3.6-flash`) because that's the key the user had — see `CLAUDE.md`'s tech-stack section
and `ROADMAP.md` §4.7/§25 for where this was updated. The agent architecture (propose → validate →
apply) is identical regardless of provider; `agents/base.py` isolates the SDK call.

## Still simplified or not built

| Gap | Why | What it would take |
|---|---|---|
| Postgres schema depth | 5 tables (citizens/households/businesses/events/simulation_state) vs. SRS §17's ~17-table wishlist | The event log (`events` table) is the real durable record; the rest are current-state projections. Splitting out dedicated `assets`/`debts`/`health_records`/etc. tables is schema work, not new capability. |
| Alembic migrations, k8s, secret managers | Not needed to demonstrate the required capability | `db/session.py`'s `create_all` is the pragmatic floor; swap in Alembic when schema changes need to be versioned. |
| World View as a literal 2D map render | Dashboard shows City/Citizen/Household/Business data as tables/metrics, not a rendered grid | `world.zones`/`world.buildings` already carry (x, y) coordinates; a Streamlit `st.pydeck_chart` or simple matplotlib grid would consume them directly. |
| A failed business can't be resurrected | `take_loan` on an inactive business adds cash/debt but doesn't flip `active` back to `True` — found live-testing the Business Agent, which correctly proposed a loan for a failed business anyway | Add a "reopen" business action, or have `_apply_loan_created` reactivate a business with `active=False` when it receives enough capital. |
| Full 1-tick-per-hour granularity | 1 tick = 1 simulated day (SRS §9 specifies hourly) | Would need a full daily-routine scheduler (wake/commute/work/lunch/shop/sleep as sub-tick phases) rather than one decision pass per day. |

## Explicitly out of scope (matches SRS §45's own list, not a cut)

Multiple cities, inter-city trade, political elections, cultural evolution, reinforcement
learning, fully LLM-controlled citizens, graph databases, PostGIS, Spark/Flink/Iceberg, Redis,
Kubernetes, distributed simulation — SRS §45 names these as future extensions beyond the current
project's own scope, not something this build cut short.
