# Life-of-100

**LIFE/100** — a depth-first, ~100-citizen digital society simulation. *Only 100 people. Every
life matters.*

This started as a 2-day vertical slice for a SIEP certificate submission covering **"Production
AI Engineering with FastAPI & Docker"** and **"Modern Data Engineering & AI Infrastructure,"**
then grew into a full pass at the original `SRS.md`/`ROADMAP.md` vision (all four AI agents, the
full disaster system, alternate-history branching, real Snowflake, and more). **`SCOPE.md`** is
the up-to-date, honest gap analysis — read that first if you're evaluating this against the full
spec; it tracks what's still simplified rather than pretending everything is 1:1 with the SRS.

## What it demonstrates

- **FastAPI** — the primary interface, ~30 endpoints across simulation control, citizens,
  businesses, events/causality, disasters, all four AI agents, alternate timelines, and
  observability (`/docs` for interactive Swagger/OpenAPI).
- **Docker** — `docker-compose.yml` orchestrates Postgres, Redpanda (Kafka-API-compatible),
  the API, a Kafka-consumer worker, and a Streamlit dashboard.
- **A modern data engineering pipeline** — simulation → immutable events → Redpanda → consumer
  worker → Postgres (operational state) → **both** DuckDB (default analytical warehouse) **and
  real Snowflake** (opt-in, using the user's own account — verified live, see `SCOPE.md`).
- **Governed AI infrastructure** — all four SRS-specified agents (Government, Historian,
  Business, Household Decision), every one backed by Google Gemini and every one constrained to
  *propose* — a validator is the only path from a proposal to an actual state change (SRS §21).
- **A full, emergent digital society** — deterministic daily decisions (purchases, school,
  job search, healthcare, loans, socializing), life events (birth/death/marriage/divorce), a
  social relationship graph, and seven disaster types, all producing real events rather than
  scripted outcomes.
- **Explainability** — every downstream effect that has a real known cause cites it
  (`caused_by`), so causal chains and butterfly-effect tracing are queries over real evidence,
  never inferred or fabricated.
- **Counterfactual experimentation** — branch a running simulation, apply a different
  intervention to each branch, and compare real, non-scripted divergence.

## Architecture

```text
Simulation Engine (world/citizens/households/businesses/government/resources/relationships)
        |
        v
   Event (immutable, SRS §14 schema)  <-- decisions.py, life_events.py, disasters.py, agents/*
        |
        +--> EventLog (in-process, source of truth for the running API)
        |
        v
   Redpanda (Kafka-API-compatible)
        |
        v
   Consumer worker --> Postgres (operational state)
                              |
                              v
                  DuckDB (default)  /  real Snowflake (opt-in, user's own account)

FastAPI  <---calls--->  Streamlit dashboard (visual layer only, never the engine)
   |
   v
Government / Historian / Business / Household Agent (Gemini) --> Validator --> Engine --> Event
   |
   v
simulation/alternate_history.py: branch -> independent engine -> compare -> divergent events
```

## Setup

**Local (no Docker), for development/tests:**

```bash
uv sync
cp .env.example .env   # fill in GEMINI_API_KEY at minimum
uv run pytest          # 62 tests, no external infra required — all Gemini calls are mocked
```

**Full stack (Docker):**

```bash
cp .env.example .env   # fill in GEMINI_API_KEY (and SNOWFLAKE_* if you want the real path)
docker compose up --build
```

This starts Postgres (`:5432`), Redpanda (`:19092`), the API (`:8000`), the consumer worker, and
the Streamlit dashboard (`:8501`). Swagger docs: http://localhost:8000/docs

The API container also applies Postgres schema migrations on top of the zero-friction
`create_all` bootstrap:

```bash
docker exec <api-container> alembic upgrade head
```

Model changes going forward should get a matching migration: `alembic revision --autogenerate -m "..."`.

## Demo walkthrough (the original, still-reproducible drought scenario)

This reproduces deterministically from `seed=847291` (the SRS's own example seed).

**1. Start the simulation:**

```bash
curl -X POST localhost:8000/simulation/start -H "Content-Type: application/json" \
  -d '{"seed": 847291, "population": 100}'
```

**2. Trigger a drought, then advance the simulation and watch the cascade emerge — not scripted:**

```bash
curl -X POST localhost:8000/disasters/drought -H "Content-Type: application/json" \
  -d '{"duration_ticks": 20}'
curl -X POST localhost:8000/simulation/tick -H "Content-Type: application/json" -d '{"ticks": 20}'
# -> food_price_index climbs while the drought is active, layoffs and business failures emerge
#    from the tick loop recomputing every business's finances daily — not an
#    `if drought: raj.lose_job()` (see life100/simulation/economy.py).
```

**3. Ask the Historian Agent why a specific citizen's situation changed** (it can only cite real
events it was actually given — see `agents/historian.py`'s `GroundingError` check):

```bash
curl -X POST localhost:8000/ai/historian/ask -H "Content-Type: application/json" \
  -d '{"citizen_id": "cit_0065", "question": "Why did this citizen lose their job?"}'
```

**4. Trace the causal chain directly** (only ever real, recorded links — never inferred):

```bash
curl localhost:8000/events/<event_id>/causes    # what led to this event
curl localhost:8000/events/<event_id>/effects   # what it led to (butterfly effect)
```

**5. Ask the Government Agent to respond, and the Business/Household agents for their own
domains:**

```bash
curl -X POST localhost:8000/ai/government/propose
curl -X POST localhost:8000/ai/business/<business_id>/propose
curl -X POST localhost:8000/ai/household/propose -H "Content-Type: application/json" \
  -d '{"citizen_id": "cit_0065", "decision_context": "considering options after a job loss"}'
```

**6. Branch into two timelines and compare them:**

```bash
curl -X POST localhost:8000/simulation/branch -d '{"new_simulation_id": "timeline_a"}'
curl -X POST localhost:8000/simulation/branch -d '{"new_simulation_id": "timeline_b"}'
curl -X POST localhost:8000/simulation/activate/timeline_a
curl -X POST localhost:8000/ai/government/propose   # e.g. a food subsidy, only on timeline_a
curl -X POST localhost:8000/simulation/tick -d '{"ticks": 15}'
curl -X POST localhost:8000/simulation/activate/timeline_b
curl -X POST localhost:8000/simulation/tick -d '{"ticks": 15}'
curl "localhost:8000/simulation/compare?simulation_a=timeline_a&simulation_b=timeline_b"
# -> per-branch metrics + the events unique to each timeline (the divergence)
```

**7. Try the other six disasters:** `/disasters/{food-shortage,flood,earthquake,
disease-outbreak,economic-recession,energy-crisis}`.

**8. Build the analytical warehouse:**

```bash
curl -X POST localhost:8000/warehouse/build            # DuckDB (default)
curl -X POST localhost:8000/warehouse/build-snowflake   # real Snowflake, if SNOWFLAKE_* is set
```

**9. Or just use the dashboard** at http://localhost:8501 — 7 tabs covering City Dashboard,
Citizens, Households, Businesses, Events & Causality, AI Agents, and Alternate Timelines.

## Tests

```bash
uv run pytest -q
```

62 tests, no external infra required: world/population/relationship determinism, the
drought→cascade mechanism, all seven disasters, the decision engine, life events, all four
agents' validator accept/reject bounds, causal-chain tracing, alternate-history branching, and
full FastAPI end-to-end flows. All Gemini calls in the test suite are mocked (`unittest.mock`) —
no live API traffic runs during `pytest`; the walkthrough above is how to exercise the real calls.

## Project documents

- `SRS.md` — the full original specification (all 46 sections).
- `ROADMAP.md` — the full 30-milestone plan.
- `SCOPE.md` — **the current, honest gap analysis against the full spec.**
- `PROOF.md` — **the three things that actually matter: it isn't scripted, complex behavior
  emerges from simple rules, and the system supports real experimental comparison of possible
  futures — each backed by a durable, re-runnable test with real numbers, not a narrated claim.**
- `CLAUDE.md` — standing development rules (event-sourcing discipline, AI safety boundary,
  determinism, session workflow).
- `PROGRESS.md` / `WORKING_NOTES.md` — build log and task-level decisions made along the way.
