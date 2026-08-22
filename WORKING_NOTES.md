# WORKING_NOTES.md — Current Task Breakdown

Referenced by `CLAUDE.md` and `ROADMAP.md` as the place to track the current stage's task
breakdown and open decisions. See `SCOPE.md` for the up-to-date gap analysis against the full
SRS — most of what this file's earlier "Day 2" section scoped out has since been built.

---

## Post-submission: full SRS build-out (2026-08-22)

All of §6, §7, §10-29, §30-33, §35-36 implemented and verified live (62/62 tests, full
docker-compose stack, real Gemini calls, real Snowflake account). See `PROGRESS.md`'s top entry
for the detailed list and `SCOPE.md` for what's still simplified.

**Remaining, in priority order (from SCOPE.md's gap table):**
- [ ] Expand Postgres schema toward SRS §17's full table list (currently 5 tables + the event log)
- [x] Alembic migrations — `migrations/` with a real initial-schema migration, applied live
- [ ] World View as an actual rendered 2D map (coordinates already exist on `world.zones`/`buildings`)
- [ ] Business resurrection after failure (a loan currently doesn't reactivate `active=False`)
- [ ] Hourly (not daily) tick granularity, if full sub-day routines are ever wanted

---

## Submission target: 2026-08-24 (SIEP certificate — FastAPI/Docker + Data Engineering/AI Infra tracks)

### Day 1 task list
- [x] `git init`, move planning docs to repo root, create `WORKING_NOTES.md`/`SCOPE.md`
- [x] Update `CLAUDE.md`/`ROADMAP.md` AI-provider references: Anthropic → Gemini Flash
- [x] `pyproject.toml` (uv-managed), `.env.example`, `.gitignore` — `uv sync` succeeds
- [x] `life100/simulation/world.py` — World/WorldConfig, deterministic generation, tests passing
- [x] `life100/simulation/citizens.py` — Citizen dataclass
- [x] `life100/simulation/households.py` — Household/Family grouping, `generate_population(seed, n=100)`, tests passing
- [x] `life100/simulation/business.py` — Business dataclass + hiring, guarantees food_production/food_retail exist, tests passing
- [x] `life100/events/schemas.py` — Event model (pydantic), EventType enum, required fields, tests passing
- [x] `life100/events/producer.py` — `EventProducer` protocol, `InMemoryEventProducer` (default/tests) + `KafkaEventProducer` (lazy import, never blocks)
- [x] `life100/events/store.py` — `EventLog` (in-process source of truth + Historian evidence source)
- [x] `life100/simulation/engine.py` — `SimulationEngine.emit()` is the only path to state change; handler table applies events
- [x] `life100/simulation/economy.py` + `disasters.py` — tick loop, drought hook, cascade test passing (17/17 tests green, `uv run pytest`)
- [ ] `life100/db/models.py` + `session.py` — SQLAlchemy: citizens, households, businesses, events, simulation_state
- [ ] `docker-compose.yml` (Postgres + Redpanda only, for this phase) + `life100/streaming/consumer.py`

### Day 2 task list
- [x] `life100/warehouse/duckdb_pipeline.py` — fact_events/dim_citizen/dim_date (Snowflake stand-in)
- [x] `life100/agents/base.py` — Gemini client wrapper (`google-genai`), retry/backoff on 429
- [x] `life100/agents/government.py`, `life100/agents/historian.py`, `life100/agents/validator.py` + mocked-LLM tests
- [x] `life100/api/main.py` + routers (simulation, citizens, events, disasters, ai, warehouse)
- [x] `docker/Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.dashboard`; full `docker-compose.yml`; smoke test — **all 5 containers healthy, full end-to-end flow verified live** (see below)
- [x] `life100/dashboard/app.py` — thin Streamlit UI calling the FastAPI endpoints
- [ ] `README.md` — setup + Raj/drought/Historian demo walkthrough
- [ ] One final clean `docker compose down -v && up --build` + demo run for the README's numbers (Postgres volume currently has leftover events from mid-build calibration debugging)

**Live smoke test results (2026-08-22, seed 847291, n=100):**
- World-scale bug found+fixed: default 40x40 grid produced 484 businesses for
  100 citizens — incoherent. Fixed to 12x12 -> 37 businesses.
- Economy calibration bug found+fixed: `Citizen.salary` (a monthly figure,
  matching SRS's own NPR examples) was being charged as a full day's expense
  every tick, making every business insolvent from tick 1 regardless of the
  drought. Fixed via `SALARY_PERIOD_DAYS = 30` divisor in economy.py, applied
  to both business payroll expense and household income.
- Business starting cash also rescaled down (small-business-scale, not
  industrial) so a sustained drought can still plausibly push some businesses
  under within its ~20-tick duration without wiping out the whole economy.
- After both fixes: drought -> 20 ticks produced 22 JOB_LOST + 5
  BUSINESS_FAILED events out of 100 citizens/37 businesses — a believable
  partial cascade, concentrated in food-sector businesses as expected.
- Demo citizen found: **Raj Shrestha (cit_0065)**, age 57, food_production
  worker at biz_012, JOB_LOST at tick 12 — a clean, directly-attributable
  hit (food business cost pressure from the drought), good for the README.
- Government + Historian agents both tested **live against real Gemini**
  (not mocked) via the running containers: Government proposed
  `food_subsidy=0.35` with a grounded rationale citing the actual snapshot
  numbers, validator approved it; Historian correctly cited the real
  `JOB_LOST` event_id for Raj Shrestha, no fabrication.
- Gemini model name needed correcting: `gemini-2.0-flash` -> `gemini-3.6-flash`
  (the former was rejected as retired by the API itself, model updated
  everywhere including `.env.example`).

### Open assumptions / decisions made along the way
- Default seed for demo: `847291` (SRS's own example seed) — reproducible identical world.
- Default population: `n=100`.
- Postgres schema kept intentionally small (citizens, households, businesses, events,
  simulation_state) rather than the full SRS §17 table list — sufficient to demonstrate the
  operational-state pattern.
- Events table doubles as the append-only event store (source for both current-state derivation
  and DuckDB warehouse ETL) rather than a separate dedicated event-store service.
