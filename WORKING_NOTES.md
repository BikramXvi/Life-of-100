# WORKING_NOTES.md — Current Task Breakdown

Referenced by `CLAUDE.md` and `ROADMAP.md` as the place to track the current stage's task
breakdown and open decisions. See `SCOPE.md` for what's in/out of scope for the 2026-08-24
certificate submission — this file tracks the day-to-day task list within that scope.

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
- [ ] `life100/warehouse/duckdb_pipeline.py` — fact_events/dim_citizen/dim_date (Snowflake stand-in)
- [ ] `life100/agents/base.py` — Gemini client wrapper (`google-genai`), retry/backoff on 429
- [ ] `life100/agents/government.py`, `life100/agents/historian.py`, `life100/agents/validator.py` + mocked-LLM tests
- [ ] `life100/api/main.py` + routers (simulation, citizens, events, disasters, ai)
- [ ] `docker/Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.dashboard`; full `docker-compose.yml`; smoke test
- [ ] `life100/dashboard/app.py` — thin Streamlit UI calling the FastAPI endpoints
- [ ] `README.md` — setup + Raj/drought/Historian demo walkthrough
- [ ] Final end-to-end run-through before submission

### Open assumptions / decisions made along the way
- Default seed for demo: `847291` (SRS's own example seed) — reproducible identical world.
- Default population: `n=100`.
- Postgres schema kept intentionally small (citizens, households, businesses, events,
  simulation_state) rather than the full SRS §17 table list — sufficient to demonstrate the
  operational-state pattern.
- Events table doubles as the append-only event store (source for both current-state derivation
  and DuckDB warehouse ETL) rather than a separate dedicated event-store service.
