# Life-of-100

**LIFE/100** — a depth-first, ~100-citizen digital society simulation. *Only 100 people. Every
life matters.*

This build is a 2-day vertical slice for a SIEP certificate submission covering **"Production AI
Engineering with FastAPI & Docker"** and **"Modern Data Engineering & AI Infrastructure."** The
full 30-milestone vision lives in `SRS.md`/`ROADMAP.md`; exactly what was built vs. deliberately
cut for this submission (and why) is documented in **`SCOPE.md`** — read that first if you're
evaluating this against the full spec.

## What it demonstrates

- **FastAPI** — the primary interface (`/docs` for interactive Swagger/OpenAPI).
- **Docker** — `docker-compose.yml` orchestrates Postgres, Redpanda (Kafka-API-compatible),
  the API, a Kafka-consumer worker, and a Streamlit dashboard.
- **A modern data engineering pipeline** — simulation → immutable events → Redpanda → consumer
  worker → Postgres (operational state) → DuckDB (analytical warehouse, star schema).
- **Governed AI infrastructure** — a Government Agent and a Historian Agent, both backed by
  Google Gemini (Flash), that can only ever *propose*; a validator is the sole path from a
  proposal to an actual state change (SRS §21's safety boundary).
- **The core narrative**: a citizen, a drought, a genuinely emergent economic cascade, and an AI
  agent explaining why — grounded in real events, not scripted.

## Architecture

```text
Simulation Engine (world/citizens/households/businesses)
        |
        v
   Event (immutable, SRS §14 schema)
        |
        +--> EventLog (in-process, source of truth for the running API)
        |
        v
   Redpanda (Kafka-API-compatible)
        |
        v
   Consumer worker --> Postgres (operational state: citizens/households/businesses/events)
                              |
                              v
                        DuckDB (fact_events / dim_citizen / dim_date — Snowflake stand-in)

FastAPI  <---calls--->  Streamlit dashboard (visual layer only, never the engine)
   |
   v
Government Agent / Historian Agent (Gemini) --> Validator --> Engine --> Event
```

## Setup

**Local (no Docker), for development/tests:**

```bash
uv sync
cp .env.example .env   # fill in GEMINI_API_KEY at minimum
uv run pytest          # 27 tests, no external infra required — all Gemini calls are mocked
```

**Full stack (Docker):**

```bash
cp .env.example .env   # fill in GEMINI_API_KEY
docker compose up --build
```

This starts Postgres (`:5432`), Redpanda (`:19092`), the API (`:8000`), the consumer worker, and
the Streamlit dashboard (`:8501`). Swagger docs: http://localhost:8000/docs

## Demo walkthrough

This reproduces deterministically from `seed=847291` (the SRS's own example seed) — every run
with the same seed and code produces the same citizens, businesses, and cascade.

**1. Start the simulation and meet the society:**

```bash
curl -X POST localhost:8000/simulation/start -H "Content-Type: application/json" \
  -d '{"seed": 847291, "population": 100}'
# -> 100 citizens, 38 households, 37 businesses, bootstrapped into Postgres
```

**2. Trigger a drought:**

```bash
curl -X POST localhost:8000/disasters/drought -H "Content-Type: application/json" \
  -d '{"duration_ticks": 20}'
# -> food_price_index immediately jumps from 1.0 to 1.4
```

**3. Advance the simulation and watch the cascade emerge — not scripted:**

```bash
curl -X POST localhost:8000/simulation/tick -H "Content-Type: application/json" -d '{"ticks": 20}'
# -> food_price_index climbs to ~2.9 while the drought is active, then begins decaying
#    after it ends; 22 JOB_LOST + 5 BUSINESS_FAILED events emerge across the run,
#    concentrated in food-sector businesses whose costs rose directly with the food
#    price index (biz_010, biz_011, biz_012, biz_013, ...).
```

**4. Meet Raj Shrestha (`cit_0065`)** — a 57-year-old `food_production` worker who is one of the
citizens this run actually affects:

```bash
curl localhost:8000/citizens/cit_0065
curl localhost:8000/citizens/cit_0065/timeline
# -> a real JOB_LOST event at tick 12, payload: {"business_id": "biz_012",
#    "reason": "business_cost_pressure"} — this is the emergent result of the tick loop
#    recomputing his employer's finances every day, not an `if drought: raj.lose_job()`.
```

**5. Ask the Historian Agent why** (grounded in the real event above, not invented):

```bash
curl -X POST localhost:8000/ai/historian/ask -H "Content-Type: application/json" \
  -d '{"citizen_id": "cit_0065", "question": "Why did this citizen lose their job?"}'
# -> {"answer": "...", "cited_event_ids": ["evt_sim_001_00012_0013"], ...}
# The Historian is only allowed to cite event_ids that were actually handed to it as
# evidence — see agents/historian.py's GroundingError check.
```

**6. Ask the Government Agent to respond:**

```bash
curl -X POST localhost:8000/ai/government/propose
# -> Government Agent reads the live economic snapshot (food price index, average
#    household stress, unemployment), proposes a policy (e.g. a food subsidy) with a
#    numeric value and rationale, the validator checks it's within allowed bounds
#    before anything happens, and only then is it applied as a real POLICY_CHANGED
#    event. Reject a proposal by editing agents/validator.py's ALLOWED_POLICY_ACTIONS
#    bounds and re-running to see the AI_DECISION_REJECTED path instead.
```

**7. Build the analytical warehouse and query it:**

```bash
curl -X POST localhost:8000/warehouse/build
curl localhost:8000/warehouse/summary
# -> event counts by type, computed from DuckDB's fact_events table (built from
#    Postgres) — the Snowflake stand-in described in SCOPE.md.
```

**8. Or just use the dashboard** at http://localhost:8501 — the same flow with a UI:
simulation controls in the sidebar, a citizen table, an Ask-the-Historian panel, a
Propose-Policy button, and a live event feed.

## Tests

```bash
uv run pytest -q
```

27 tests, no external infra required: world/population determinism, the drought→cascade
mechanism, event schema/log behavior, the AI validator's accept/reject bounds, and full
FastAPI end-to-end flows. All Gemini calls in the test suite are mocked (`unittest.mock`) — no
live API traffic runs during `pytest`, protecting the free-tier quota; the walkthrough above is
how to exercise the real Gemini calls.

## Project documents

- `SRS.md` — the full original specification (all 46 sections).
- `ROADMAP.md` — the full 30-milestone plan this submission is a slice of.
- `SCOPE.md` — **what this submission cut from that plan, and why.**
- `CLAUDE.md` — standing development rules (event-sourcing discipline, AI safety boundary,
  determinism, session workflow).
- `PROGRESS.md` / `WORKING_NOTES.md` — build log and task-level decisions made along the way.
