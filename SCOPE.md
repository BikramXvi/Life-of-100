# SCOPE.md — Submission Scope for LIFE/100

`SRS.md` and `ROADMAP.md` describe the full 30-milestone LIFE/100 vision. This document records
what was deliberately built (and deliberately cut) for the **SIEP certificate submission due
2026-08-24**, covering the "Production AI Engineering with FastAPI & Docker" and "Modern Data
Engineering & AI Infrastructure" tracks. This is a documented, intentional scope reduction under
a 2-day deadline — not scope creep and not silent drift from the spec.

## What this submission demonstrates

- **FastAPI**: the primary interface. Real endpoints for simulation control, citizens, events,
  disasters, and AI agents, with auto-generated Swagger/OpenAPI docs.
- **Docker**: `Dockerfile`s for the API, the Kafka-consumer worker, and the dashboard, orchestrated
  via `docker-compose.yml` alongside Postgres and Redpanda.
- **Modern data engineering pipeline**: simulation → immutable events → Redpanda (Kafka-API
  compatible) → consumer → Postgres (operational state) → DuckDB (analytical warehouse, star
  schema fact/dim tables).
- **AI infrastructure with a safety boundary**: a Government Agent (propose → validate → apply)
  and a Historian Agent (evidence-grounded explanation, must cite real event IDs), both backed by
  Gemini Flash (free tier), never allowed to touch simulation state directly.
- **The core narrative**: a citizen, a drought, a real cascading economic effect, and an AI agent
  explaining why — all backed by actual events, not scripted output.

## What was cut, and why

| Cut | Reason | Future path |
|---|---|---|
| Snowflake | No account provisioned in the 2-day window | DuckDB stand-in reads the same event/Postgres data; swapping in real Snowflake is a warehouse-layer change only |
| Business Agent, Household Decision Agent | Time; Government + Historian already demonstrate the two core AI-infra patterns (constrained proposal, grounded explanation) | `agents/base.py` is a shared framework — adding either agent follows the same ~1-file pattern as Government/Historian |
| Alternate timelines / branching, timeline comparison | Out of scope for this submission's tracks | Full ROADMAP Phase 12 (Steps 29) |
| Causal-graph visualization, life replay UI | Out of scope for this submission's tracks | Full ROADMAP Phase 11 (Steps 27-28) |
| Disaster types beyond drought | One disaster is enough to prove the cascade mechanism | Flood/earthquake/etc. follow the same `disasters.py` pattern |
| Full tick-by-tick daily routines (wake/commute/work/lunch/shop/sleep per citizen) | Time; replaced with a simplified per-tick economic/employment update that still emits real events and a genuine cascade | ROADMAP Step 10 |
| 1 tick = 1 simulated hour (SRS §9) | Simplified to 1 tick = 1 simulated day, so a demo-length run (a few dozen ticks) covers enough simulated time for the economy/cascade to visibly play out | Re-introduce hour-level ticks if/when full daily routines (above) are built |
| Alembic migrations, k8s, secret managers, elaborate monitoring | Not needed to demonstrate the required tracks | `Dockerfile`/`docker-compose.yml`/health checks/`.env` are the "production" floor for this submission |
| AI provider: Gemini Flash (free tier) instead of Anthropic/Claude | User has a Gemini key, not an Anthropic key, for this submission | `agents/base.py` isolates the SDK call; swapping providers again is a contained change |

## What was kept at full spec

- **Population**: ~100 citizens, as specified — looping over more citizens costs no extra
  development time, only per-citizen behavioral depth was reduced.
- **Event schema** (`event_id`, `event_type`, `schema_version`, `simulation_id`,
  `simulation_tick`, `simulation_time`, `source_entity`, `source_type`, `city_id`, `payload`) —
  used exactly as SRS §14 defines it.
- **Determinism**: world/citizen generation is seeded and reproducible (SRS §7, §35).
- **The AI safety boundary**: agent → proposed decision → validator → simulation engine → event
  is non-negotiable and implemented exactly as SRS §21 specifies, regardless of provider.
