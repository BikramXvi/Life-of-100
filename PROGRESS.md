# Progress Log

Newest entries at the top. Each entry: date, SRS stage/section, what was done, what's next.

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
warehouse/database/schema not yet provisioned — see `SCOPE.md`).

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
  simulation_state tables.
- `docker-compose.yml` bringing up Postgres + Redpanda; `life100/streaming/consumer.py` — a Kafka
  consumer that idempotently upserts events into Postgres.
- Then Day 2: DuckDB warehouse pipeline, Government + Historian Gemini agents + validator, FastAPI
  app, Dockerfiles, thin Streamlit dashboard, README/demo script.
- **Assumption to confirm later:** 1 tick = 1 simulated day for this submission (SRS's own "1
  tick = 1 hour" granularity is simplified — see `SCOPE.md`).
