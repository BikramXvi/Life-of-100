# CLAUDE.md — Standing Instructions for LIFE/100

This file is read by Claude Code at the start of every session in this repo.
The full spec lives in `SRS.md` — read the relevant section before starting
any task. Do not rely on memory of the spec from a previous session; re-read it.

## What this project is


A depth-first, ~100-citizen digital society simulation. See `SRS.md` §1–5 for
the full picture. The one-line version: citizens make deterministic day-to-day
decisions, meaningful actions become immutable events, events stream through
Kafka into Postgres (current state) and later Snowflake (history), and a small
set of AI agents propose — never directly make — high-level decisions.

## Ground rules

1. **Follow the build order in SRS.md §39. Do not build ahead of the current
   stage.** If asked to work on something from a later stage, say so and ask
   whether to proceed anyway. This project's biggest risk is scope creep, not
   missing features — infra (Kafka/Snowflake) is worthless without a working
   citizen/economy loop underneath it (§27, §29 of the original spec review).
2. **Every session should be scoped to one small, reviewable unit of work** —
   one entity model, one event type, one API endpoint, one agent — not a whole
   stage in one shot. This repo is being built on a usage-limited plan; small,
   completable tasks beat sprawling ones. See `WORKING_NOTES.md` for how to
   split a stage into sessions.
3. **Testability without Godot** (SRS §27 "Development Principles" concept):
   every simulation/economy/event feature must be testable via unit tests or
   CLI, never requiring the Godot client to verify correctness.
4. **Events are the source of truth.** Any state change to a citizen,
   household, business, or government must go through the event system
   (`events/schemas`, `events/producers`) — never mutate state directly, even
   before Kafka exists (Stage 5 introduces the event system; Stage 6 adds
   Kafka as the transport — the discipline of "state changes only via events"
   starts at Stage 5, not Stage 6).
5. **Follow the event schema exactly** as defined in SRS.md §14, including
   `schema_version`. If a new event type needs a field the schema doesn't
   support, update the schema and bump the version — don't bolt on ad hoc
   fields.
6. **AI agents never touch state directly** (SRS §21). Agent code proposes an
   action; a validator checks it; only the simulation engine applies it. This
   applies even to placeholder/stub agents built early for testing.
7. **Snowflake must never be on the simulation's critical path** (SRS §18).
   If a task would make the simulation depend on Snowflake responding, stop
   and flag it instead of implementing it that way.
8. **Determinism matters.** World generation and (as far as practical)
   simulation behavior must be reproducible from a seed (SRS §7, §35). Avoid
   unseeded randomness (`Math.random()`, unseeded `random.random()`, etc.) in
   simulation code — use a seeded RNG passed through explicitly.
9. **After finishing a task, update `PROGRESS.md`** with what was built, what
   stage/section of the SRS it maps to, and what's next. This is how context
   carries across sessions without re-explaining everything each time.
10. **Don't invent scope.** If the SRS is ambiguous about a detail (e.g. exact
    personality-trait model, exact decision-scoring formula), propose a
    concrete, simple default, note the assumption in `PROGRESS.md`, and move
    on — don't stall waiting for clarification unless it would affect the
    data model in a hard-to-reverse way.

## Tech stack (fill in / confirm before Stage 1)

- Language/runtime: _TBD — pick one and record it here (e.g. Python 3.12 +
  FastAPI, or TypeScript + Node)_
- Local infra: Docker Compose for Postgres + Kafka (Redpanda is a lighter
  Kafka-compatible alternative if resources are tight)
- Snowflake: real account or a local stand-in (e.g. DuckDB) until Stage 9 —
  decide when you get there, not before
- Godot: version _TBD_, integrates via the API layer only, never talks to the
  DB or Kafka directly
- AI agents: Claude via the Anthropic API (not Claude Code itself) — agent
  code should call the API directly with tool use for proposing actions

## Session workflow (Claude Pro usage discipline)

Claude Code sessions on the Pro plan run on a rolling 5-hour / weekly limit
shared with claude.ai. To stay productive:

- **Scope each session to one task from `WORKING_NOTES.md`'s current stage
  before starting.** Say the scope out loud at the start of the session.
- **Prefer Sonnet for implementation work; reserve Opus (if available) for
  planning/architecture decisions** that are hard to reverse.
- **Clear/restart context between unrelated tasks** rather than letting one
  thread sprawl across a whole stage.
- **Commit at the end of every completed task**, with a message referencing
  the SRS section (e.g. `feat(citizens): add Citizen entity model (SRS §6.1)`).
- If a task turns out to be bigger than expected mid-session, stop, commit
  what works, and split the remainder into a fresh session rather than
  pushing through.

## Repository structure

See `SRS.md` §38 for the full target layout. Don't create directories for
subsystems that haven't been reached yet in the build order — an empty
`warehouse/snowflake/` sitting there from Stage 1 is a sign scope crept ahead
of schedule.

## Files Claude should keep updated

- `PROGRESS.md` — running log of what's been built, by SRS section/stage
- `WORKING_NOTES.md` — the current stage's task breakdown and any open
  assumptions/decisions made along the way
- `ARCHITECTURE.md` — created once real architectural decisions exist (tech
  stack, module boundaries) — not needed on day one
