# LIFE/100 — Software Requirements Specification

> **Tagline:** Only 100 people. Every life matters.

> **Implementation status:** This is the original specification — the fixed target, not a log of
> what's built. For current implementation status against every section here, see `SCOPE.md` (the
> honest, up-to-date gap analysis) and `PROGRESS.md` (the build history). A few sections carry a
> short `> **Status:**` note directly below their heading where the implementation reached a
> deliberate, non-obvious point worth flagging in place — those are the exception, not the rule;
> most sections are left unannotated and `SCOPE.md` remains the authoritative tracker.

---

## 1. Executive Summary

**LIFE/100** is an interactive, data-driven simulation of a small digital society consisting of approximately **100 deeply modeled citizens**.

Unlike conventional city or civilization simulators that prioritize population scale, LIFE/100 prioritizes:

* Individual depth
* Behavioral realism
* Historical traceability
* Social relationships
* Economic interaction
* Explainable emergent behavior
* Reproducibility
* Counterfactual experimentation

Every citizen possesses a persistent digital life consisting of:

* Personal identity
* Family structure
* Education
* Employment
* Income and wealth
* Health
* Personality traits
* Goals and preferences
* Relationships
* Daily routines
* Consumption patterns
* Decisions
* Memories
* Life events
* Historical records

Every meaningful action within the simulation produces a structured, immutable event. The system therefore operates as both a **living interactive simulation** and a **large historical data-generation system**.

### Core Architecture

```text
                         WEB DASHBOARD
                           Streamlit
                               |
                               v
                     +-------------------+
                     |  Simulation Engine |
                     +-------------------+
                               |
                  +------------+------------+
                  |                         |
                  v                         v
            WORLD STATE                EVENT ENGINE
                  |                         |
                  |                         v
                  |                       KAFKA
                  |                    Event Stream
                  |                         |
                  |              +----------+----------+
                  |              |                     |
                  v              v                     v
             PostgreSQL       Consumers            AI Agents
            Current State        |                     |
                                 |                     v
                                 |              Policy Validator
                                 |                     |
                                 +----------> Simulation Engine
                                 |
                                 v
                             Snowflake
                          Full History
                                 |
                                 v
                            Analytics
```

The system allows users to:

* Observe individual lives
* Investigate historical events
* Analyze social and economic relationships
* Introduce controlled disasters
* Interact with AI decision-makers
* Trace causal relationships
* Create counterfactual alternate timelines
* Compare different simulation outcomes

---

# 2. Vision

The system should allow users to ask questions such as:

* Why did this person become poor?
* Why did this business fail?
* Why did this family migrate?
* Who influenced this decision?
* What caused food prices to rise?
* What would have happened if the government had acted differently?
* What happens if one person's life takes a different path?

The system should not merely show **what happened**.

It should be capable of explaining:

1. What happened?
2. Why did it happen?
3. What caused it?
4. Who was affected?
5. What happened afterward?
6. What could have happened differently?

---

# 3. Core Design Philosophy

## 3.1 Depth Over Scale

Population is deliberately capped at approximately **100 citizens**.

The objective is to model a small number of individuals with extraordinary depth rather than millions of shallow entities.

---

## 3.2 History Over State

Current state alone is not sufficient.

The system must preserve the events that produced the current state.

```text
Current Wealth
    |
    +-- Why?
        |
        +-- Salary
        +-- Expenses
        +-- Investments
        +-- Debt
        +-- Medical Costs
        +-- Major Life Events
```

---

## 3.3 Emergence Over Scripting

Outcomes should emerge from interactions rather than predefined scripts.

### Avoid

```text
"Raj becomes unemployed in year 12."
```

### Prefer

```text
Business Decline
       |
       v
Revenue Decreases
       |
       v
Cost Reduction
       |
       v
Employee Layoffs
       |
       v
Raj Loses Job
```

---

## 3.4 Explainability

Every major change should be traceable.

The system should answer:

* **WHAT** happened?
* **WHY** did it happen?
* **WHAT EVENTS** caused it?
* **WHO** was affected?
* **WHAT HAPPENED AFTERWARD?**

---

## 3.5 Controlled Experimentation

Users should be able to change one or more conditions and compare resulting outcomes.

Examples include:

* Government policy changes
* Disaster intervention
* Tax changes
* Subsidies
* Economic conditions
* Household decisions

---

# 4. Project Objectives

| ID  | Objective                                                                        |
| --- | -------------------------------------------------------------------------------- |
| O1  | Deep Individual Simulation — approximately 100 citizens with detailed attributes |
| O2  | Persistent Digital Lives — complete historical record per citizen                |
| O3  | Emergent Society — interactions create unexpected outcomes                       |
| O4  | Event-Driven Architecture — immutable structured events                          |
| O5  | Real-Time Data Engineering — Kafka streaming                                     |
| O6  | Operational Data Storage — PostgreSQL                                            |
| O7  | Analytical Data Warehouse — Snowflake                                            |
| O8  | AI Decision Making — constrained agents                                          |
| O9  | Explainable AI — evidence-backed explanations                                    |
| O10 | Causal Analysis — event-to-consequence tracing                                   |
| O11 | Counterfactual Simulation — branching and comparison                             |
| O12 | Interactive Visualization — Web Dashboard interface                              |

---

# 5. System Scope

The simulation consists of:

* 1 city
* Approximately 100 citizens
* Families and households
* Businesses
* Schools
* Healthcare
* Banking
* Government
* Infrastructure
* Environment
* Economy
* Social network
* Simulation engine
* Event platform
* Databases
* AI agents
* Web dashboard

Performance optimization targets simulation complexity and event generation rather than population scale.

---

# 6. System Entities

## 6.1 Citizen

### Identity

* ID
* Name
* Age
* Date of birth
* Gender
* Nationality
* Home

### Education

* Education level
* School
* University
* Skills
* Academic performance

### Employment

* Occupation
* Employer
* Salary
* Employment history
* Experience
* Job satisfaction

### Financial

* Income
* Savings
* Debt
* Assets
* Credit score
* Expenses
* Investments

### Health

* Health score
* Fitness
* Stress
* Sleep
* Medical history
* Healthcare usage

### Psychological

* Personality traits
* Risk tolerance
* Ambition
* Patience
* Social tendency
* Decision preferences

### Behavioral

* Daily routine
* Consumption preferences
* Spending habits
* Travel patterns
* Leisure activities

### Goals

* Career goals
* Financial goals
* Family goals
* Personal goals
* Long-term aspirations

### Relationships

* Family
* Friends
* Coworkers
* Neighbors
* Teachers
* Employers

---

## 6.2 Household

A household contains:

* ID
* Members
* Property
* Income
* Expenses
* Savings
* Debt
* Assets
* Goals
* Financial stress
* Living conditions

Household decisions can affect every member.

---

## 6.3 Family

### Relationships

* Parent
* Child
* Sibling
* Spouse
* Partner

### Family Events

```text
MARRIAGE
DIVORCE
CHILD_BORN
DEATH
FAMILY_MOVED
```

---

## 6.4 Business

A business contains:

* ID
* Industry
* Owner
* Employees
* Revenue
* Expenses
* Profit
* Cash
* Inventory
* Debt
* Customers
* Products
* Location

### Business Actions

* Hire
* Fire
* Produce
* Sell
* Purchase
* Borrow
* Invest
* Expand
* Contract
* Fail

---

## 6.5 Government

Government policies include:

* Tax rate
* Interest rate
* Food subsidies
* Healthcare spending
* Education spending
* Infrastructure spending
* Business regulation
* Environmental regulation

---

## 6.6 Infrastructure

Infrastructure includes:

* Homes
* Roads
* Schools
* Hospitals
* Shops
* Factories
* Banks
* Government buildings
* Parks
* Utilities

---

## 6.7 Resources

Resources include:

* Food
* Water
* Energy
* Land
* Raw materials

---

# 7. World Generation

The system must procedurally generate:

* Terrain
* Roads
* Residential areas
* Commercial areas
* Industrial areas
* Schools
* Hospitals
* Government buildings
* Businesses
* Homes
* Natural resources

World generation must be **deterministic** based on a simulation seed.

Example:

```text
Seed: 847291
```

The same seed combined with the same configuration must reproduce identical initial conditions.

---

# 8. Simulation Engine

The simulation engine manages:

* Time
* Citizens
* Households
* Businesses
* Government
* Economy
* Environment
* Relationships
* Events

### Architectural Rule

The core simulation engine **MUST NOT use `pandas` or `numpy` for state management**.

Use:

* Standard Python dictionaries
* `dataclasses`
* Plain Python loops
* Simple data structures

Optimization should only be introduced after profiling identifies a specific bottleneck.

---

# 9. Simulation Time

> **Status:** Implemented as literally specified — `engine.tick` is the hourly counter (1 tick = 1
> simulated hour), with `engine.day`/`engine.hour_of_day` derived from it. Every event carries a
> real `simulation_tick` (hourly). Pause/Resume/Step/x1/x10/x100/x1000 are not implemented as named
> playback controls — the API's `/simulation/tick` (advance N hours or N days) serves the same
> purpose without the named-speed abstraction. See `SCOPE.md`'s "Closed since the last pass:
> hourly tick granularity" for the full implementation note.

Simulation time is separate from real-world time.

Example:

```text
1 tick = 1 simulated hour
```

Supported controls:

* Pause
* Resume
* Step
* x1
* x10
* x100
* x1000

### Architectural Rule

Simulation time is the absolute source of truth.

The following values must be attached to all meaningful events:

```text
sim_tick
sim_day
sim_year
```

Wall-clock time is irrelevant to the analytical data warehouse.

---

# 10. Daily Life Simulation

> **Status:** Implemented as a scheduled decision engine, not a full sub-tick activity
> simulation — `decisions.py` dispatches each decision type (school, purchases, job search,
> healthcare/loans, socializing) at a specific hour of the simulated day instead of running a
> distinct phase for every routine step below. Modified-by factors (employment, health, family,
> weather/disasters, income, stress, goals, unexpected events) are real and mechanically wired
> in, not simplified away — only the routine's granularity is a scheduled-dispatch approximation
> rather than a literal Wake→Breakfast→Commute→...→Sleep state machine per citizen.

Citizens follow dynamic routines such as:

```text
Wake
  |
Breakfast
  |
Commute
  |
Work / School
  |
Lunch
  |
Shopping / Recreation
  |
Family / Social Time
  |
Sleep
```

Routines are modified by:

* Employment
* Health
* Family
* Weather
* Income
* Stress
* Goals
* Unexpected events

---

# 11. Decision System

Citizen decisions may include:

* Purchase food
* Go to work
* Change job
* Save money
* Take a loan
* Visit hospital
* Move house
* Attend school
* Socialize
* Start a business
* Invest

### AI Usage Rule

Normal low-level decisions should use deterministic simulation logic.

AI should primarily be used for:

* Complex decisions
* Strategic decisions
* Policy decisions
* High-impact decisions
* Historical reasoning

---

# 12. Social Network

The society is represented as a dynamic relationship graph.

Each relationship contains:

* Type
* Strength
* Trust
* Frequency
* History
* Last interaction

Example:

```text
Raj
 |
 +-- Maya   -> Spouse     -> 0.94
 +-- John   -> Friend     -> 0.78
 +-- David  -> Coworker   -> 0.62
 +-- Sarah  -> Neighbor   -> 0.31
```

---

# 13. Economic Simulation

The economic system models:

* Employment
* Income
* Consumption
* Prices
* Production
* Inventory
* Savings
* Debt
* Loans
* Taxes
* Business revenue
* Business costs

Example economic cascade:

```text
Food Demand
     |
     v
Inventory Decreases
     |
     v
Price Increases
     |
     v
Household Expenses Increase
     |
     v
Savings Decrease
```

---

# 14. Event Architecture

Every meaningful action must generate an immutable event.

### Example Event

```json
{
  "event_id": "evt_839201",
  "event_type": "JOB_LOST",
  "schema_version": 1,
  "simulation_id": "sim_001",
  "simulation_tick": 18291,
  "simulation_time": "YEAR_12_MONTH_04_DAY_17",
  "source_entity": "cit_023",
  "source_type": "citizen",
  "city_id": "city_001",
  "payload": {
    "business_id": "biz_004",
    "previous_salary": 2400,
    "reason": "business_downsizing"
  }
}
```

### Required Fields

Every event must contain:

* `event_id`
* `event_type`
* `schema_version`
* `simulation_id`
* `simulation_tick`
* `simulation_time`
* `source_entity`
* `source_type`
* `city_id`
* `payload`

---

# 15. Event Types

The system should support at least the following event types:

```text
CITIZEN_BORN
CITIZEN_DIED
MARRIAGE
DIVORCE
CHILD_BORN
MOVED

JOB_STARTED
JOB_LOST
PROMOTION
SALARY_CHANGED

PURCHASE
SALE

LOAN_CREATED
LOAN_REPAID
LOAN_DEFAULTED

BUSINESS_CREATED
BUSINESS_EXPANDED
BUSINESS_CONTRACTED
BUSINESS_FAILED

PROPERTY_PURCHASED
PROPERTY_SOLD

MEDICAL_VISIT
SCHOOL_ATTENDED

RELATIONSHIP_CREATED
RELATIONSHIP_CHANGED
RELATIONSHIP_ENDED

TAX_PAID
POLICY_CHANGED

RESOURCE_EXTRACTED

DISASTER_STARTED
DISASTER_ENDED

AI_DECISION_PROPOSED
AI_DECISION_ACCEPTED
AI_DECISION_REJECTED
```

---

# 16. Kafka Event Streaming

Kafka topics:

```text
citizens
families
economy
businesses
relationships
government
health
environment
disasters
ai-decisions
system-events
```

### Architectural Rule

The simulation **MUST NEVER block waiting for Kafka**.

The simulation should:

1. Generate an event.
2. Push the event to an event interface.
3. Continue to the next simulation operation.

Kafka provides:

* Durability
* Decoupling
* Replay
* Asynchronous processing
* Scalability
* Event ordering where required

---

# 17. PostgreSQL Operational Database

PostgreSQL stores the current operational state of the simulation.

### Core Tables

```text
citizens
households
families
relationships
businesses
employees
transactions
assets
debts
health_records
education
locations
infrastructure
government
policies
simulation_state
agents
```

PostgreSQL should answer questions such as:

* Where does Raj currently live?
* Who is employed at Company X?
* What is Household 17's current debt?
* What is the current population?

---

# 18. Snowflake Analytical Warehouse

> **Status:** Implemented with a real Snowflake account (not mocked) — `warehouse/
> snowflake_pipeline.py` provisions the warehouse/database/schema on first use and loads
> `fact_events`/`dim_citizen` from Postgres, verified live loading 1.79M real events. A DuckDB
> stand-in (`warehouse/duckdb_pipeline.py`) remains the default/test-covered path since it needs
> no external account. Core datasets: only `fact_events`/`dim_citizen` are modeled, not the full
> 12-dataset list below — the event log already carries most of that data (household finances,
> employment history, disaster impact, etc. are all derivable from it), so the remaining datasets
> are a modeling/materialization gap, not a missing capability. The critical-path constraint below
> is honored: `/warehouse/build-snowflake` is a separate, opt-in endpoint the simulation never
> calls internally.

Snowflake stores historical analytical data.

### Core Datasets

```text
citizen_life_history
household_finances
employment_history
economic_activity
business_performance
relationship_changes
migration_patterns
wealth_distribution
health_trends
policy_effects
disaster_impact
decision_history
```

### Constraint

Snowflake **MUST NOT** be part of the critical simulation execution path.

The simulation must continue operating if Snowflake is temporarily unavailable.

---

# 19. Analytical Model

## 19.1 Fact Tables

```text
fact_transactions
fact_employment
fact_citizen_events
fact_household_finance
fact_business_activity
fact_relationship_events
fact_policy_effects
fact_health_events
```

## 19.2 Dimension Tables

```text
dim_citizen
dim_household
dim_family
dim_business
dim_city
dim_date
dim_location
dim_product
```

---

# 20. AI Agent Architecture

AI agents operate at higher levels.

LLMs should **not** be used for every routine citizen action.

---

## 20.1 Government Agent

### Analyzes

* Inflation
* Unemployment
* Food prices
* Household stress
* Business failures
* Tax revenue
* Economic growth

### Proposes

* Tax changes
* Subsidies
* Interest rate changes
* Government spending
* Emergency policies

---

## 20.2 Business Agent

### Analyzes

* Demand
* Revenue
* Inventory
* Costs
* Competition
* Employees
* Loans

### Proposes

* Hiring
* Firing
* Price changes
* Production changes
* Expansion
* Loans

---

## 20.3 Household Decision Agent

The household agent is activated only for significant decisions, such as:

* Job opportunities
* Moving house
* Major loans
* Education
* Business investment

The agent receives relevant evidence and evaluates trade-offs.

---

## 20.4 Historian Agent

The Historian Agent answers questions such as:

> Why did Raj become unemployed?

The Historian Agent **MUST cite underlying events and evidence** rather than fabricate explanations.

---

# 21. AI Safety Boundary

AI agents must **never directly modify simulation state**.

The required flow is:

```text
AI Agent
   |
   v
Proposed Decision
   |
   v
Policy / Action Validator
   |
   v
Validation
   |
   v
Simulation Engine
   |
   v
World State Change
   |
   v
Event Generated
```

The validator checks:

* Valid action
* Valid parameters
* Allowed authority
* Economic constraints
* Simulation rules
* Safety constraints

---

# 22. Explainability Engine

Every significant state change should have an explanation path that users can navigate backward.

Example:

```text
Raj Wealth Decreased 31%
          |
          v
Income Decreased
          |
          v
Job Lost
          |
          v
Business Revenue Decreased
          |
          v
Demand Decreased
          |
          v
Food Prices Increased
          |
          v
Household Expenses Increased
```

---

# 23. Causal Graph

The system should represent causal chains such as:

```text
DROUGHT
   |
   v
CROP_FAILURE
   |
   v
FOOD_SHORTAGE
   |
   v
FOOD_PRICE_INCREASE
   |
   v
HOUSEHOLD_EXPENSE_INCREASE
   |
   v
SAVINGS_DECLINE
   |
   v
DEBT_INCREASE
   |
   v
FINANCIAL_STRESS
```

Causal graphs should be visualized within the Web Dashboard.

---

# 24. Life Replay

Every citizen should have a chronological, replayable historical timeline.

Example:

```text
Birth
  |
  v
School
  |
  v
Graduation
  |
  v
University
  |
  v
First Job
  |
  v
Marriage
  |
  v
First Child
  |
  v
House Purchase
  |
  v
Job Loss
  |
  v
New Business
  |
  v
Current State
```

---

# 25. Memory System

Citizens maintain structured memories of significant events.

Examples:

* First job
* Marriage
* Birth of child
* Major financial loss
* Death of family member
* Business failure
* Major achievement

Memories should influence future behavior where appropriate.

---

# 26. Disaster System

Users can trigger controlled disasters such as:

* Drought
* Flood
* Earthquake
* Disease outbreak
* Economic recession
* Food shortage
* Energy crisis

Example:

```text
DROUGHT
   |
   v
Food Production Decreases
   |
   v
Food Supply Decreases
   |
   v
Food Prices Increase
   |
   v
Household Costs Increase
   |
   v
Business Costs Increase
   |
   v
Profit Decreases
   |
   v
Layoffs
   |
   v
Unemployment Increases
```

---

# 27. Counterfactual / Alternate History Engine

Users can branch from a previous simulation state.

Each branch preserves:

* Original seed
* Parent simulation
* Branch point
* Configuration
* Policy differences
* Simulation version
* AI model version

---

# 28. Timeline Comparison

The system should support comparisons such as:

| Metric           | Subsidy | No Action |
| ---------------- | ------: | --------: |
| Population       |      97 |        89 |
| Food Price       |     +8% |      +71% |
| Unemployment     |      6% |       17% |
| Average Wealth   |    +12% |      -43% |
| Business Count   |      14 |         9 |
| Household Stress |     31% |       67% |

The system should identify which events caused the divergence between timelines.

---

# 29. Butterfly Effect Analysis

The system should allow users to investigate how small changes propagate through the society.

Example:

```text
Citizen spends NPR 500 instead of NPR 300
              |
              v
Household Savings Change
              |
              v
Business Revenue Change
              |
              v
Inventory / Demand Change
              |
              v
Employment Change
              |
              v
Wealth Distribution Change
              |
              v
Economic Output Change
              |
              v
Migration / Social Effects
```

The system should trace downstream effects across:

* Households
* Businesses
* Employment
* Wealth
* Economic output
* Migration
* Social relationships

---

# 30. Web Dashboard Interface

The Streamlit dashboard should provide the following views.

## 30.1 World View

Displays:

* City
* Homes
* Roads
* Businesses
* Schools
* Hospitals
* Citizens

Rendered using 2D grid/map-style visualizations.

---

## 30.2 Citizen View

Displays:

* Identity
* Family
* Employment
* Finance
* Health
* Relationships
* Goals
* Current activity
* Historical timeline

---

## 30.3 Household View

Displays:

* Members
* Income
* Expenses
* Assets
* Debt
* Stress
* History

---

## 30.4 Business View

Displays:

* Employees
* Revenue
* Costs
* Inventory
* Profit
* History

---

## 30.5 City Dashboard

Displays:

* Population
* GDP
* Inflation
* Employment
* Average wealth
* Migration
* Business activity

---

## 30.6 Event Stream

Provides an auto-scrolling live event feed.

The event stream should consume events through Kafka or a suitable asynchronous consumer layer.

---

## 30.7 AI Chat

Embedded chat interface for querying:

* Historian Agent
* Government Agent
* Other approved AI agents

---

# 31. Visualization Modes

The dashboard should provide the following visualization modes:

* Human
* Economic
* Social
* Environmental
* Causal
* Historical

These modes should be switchable through dashboard controls.

---

# 32. User Interaction

Users should be able to:

* Start the simulation
* Pause the simulation
* Change simulation speed
* Step through simulation ticks
* Inspect citizens
* Inspect families
* Inspect businesses
* Inspect relationships
* Inspect events
* Trigger disasters
* Change policies
* Ask AI questions
* Replay individual lives
* Inspect causal chains
* Create alternate timelines
* Compare timelines

---

# 33. Performance Requirements

Target population:

```text
~100 citizens
```

The project prioritizes **simulation depth over population scale**.

The system should monitor:

* Ticks/sec
* Events/sec
* Event processing latency
* Kafka throughput
* Kafka lag
* PostgreSQL query latency
* Snowflake query latency
* AI decision latency
* Dashboard rendering performance
* Memory usage
* CPU usage

---

# 34. Reliability Requirements

The system must handle:

* Duplicate events
* Kafka interruptions
* Database failures
* Malformed events
* Invalid AI decisions
* Simulation restart
* Incomplete transactions
* AI timeouts
* Snowflake unavailability

Appropriate logging, validation, error handling, and recovery mechanisms are required.

---

# 35. Reproducibility

The system must record:

* Simulation ID
* Random seed
* Initial world configuration
* Initial citizen data
* Initial policies
* Simulation version
* Event schema version
* AI model version
* Agent configuration

A simulation should be reproducible when these parameters are preserved.

---

# 36. Observability

The system should expose:

* Simulation ticks/sec
* Events/sec
* Kafka lag
* Database latency
* AI decisions
* AI latency
* Failed events
* CPU usage
* Memory usage
* Current simulation time
* Active citizens
* Active businesses

---

# 37. Security

Credentials must never be hardcoded.

Environment variables should be used for:

```text
KAFKA credentials
POSTGRESQL credentials
SNOWFLAKE credentials
AI API keys
```

AI agents must operate only through controlled tools and validated actions.

---

# 38. Repository Structure

```text
life100/
│
├── simulation/
│   ├── citizens/
│   ├── households/
│   ├── families/
│   ├── businesses/
│   ├── economy/
│   ├── government/
│   ├── environment/
│   ├── relationships/
│   └── world/
│
├── events/
│   ├── schemas/
│   ├── producers/
│   └── validators/
│
├── streaming/
│   ├── kafka/
│   └── consumers/
│
├── database/
│   ├── postgres/
│   └── migrations/
│
├── warehouse/
│   ├── snowflake/
│   ├── models/
│   └── analytics/
│
├── agents/
│   ├── government/
│   ├── business/
│   ├── household/
│   └── historian/
│
├── alternate_history/
│
├── api/
│
├── dashboard/
│   ├── views/
│   ├── components/
│   └── app.py
│
├── tests/
│
├── docker/
│
├── docs/
│
├── SRS.md
├── ARCHITECTURE.md
└── AGENTS.md
```

---

# 39. Development Workflow

Development must follow **vertical slices in the following order**.

## Phase 1 — World

Implement:

* Procedural city
* Homes
* Roads
* Businesses
* Infrastructure

---

## Phase 2 — Citizens

Implement:

* Approximately 100 citizens
* Families
* Households
* Personal attributes
* Relationships

---

## Phase 3 — Daily Life

Implement:

* Movement
* Work
* School
* Shopping
* Sleep
* Social interaction

---

## Phase 4 — Economy

Implement:

* Employment
* Income
* Consumption
* Businesses
* Prices
* Savings
* Debt

---

## Phase 5 — Event System

Implement:

```text
Every meaningful action
        |
        v
Structured Event
```

---

## Phase 6 — Kafka

Implement:

```text
Event Generation
       |
       v
Kafka
       |
       v
Consumers
```

---

## Phase 7 — PostgreSQL

Implement:

```text
Current World State
       |
       v
PostgreSQL
```

---

## Phase 8 — Dashboard

Implement:

```text
Simulation
    |
    v
API
    |
    v
Streamlit Web UI
```

---

## Phase 9 — Snowflake

Implement:

```text
Kafka
   |
   v
Analytical Warehouse
   |
   v
Snowflake
```

---

## Phase 10 — AI

Implement:

* Government Agent
* Business Agent
* Household Agent
* Historian Agent

---

## Phase 11 — Explainability

Implement:

```text
Event History
      |
      v
Causal Graph
      |
      v
Explanation
```

---

## Phase 12 — Disasters

Implement:

* Drought
* Flood
* Economic crisis
* Other controlled disasters

---

## Phase 13 — Alternate History

Implement:

```text
Simulation Snapshot
       |
       v
Branch
       |
       v
Simulate
       |
       v
Compare
```

---

## Phase 14 — Showcase

Integrate the complete system into a coherent demonstration narrative.

### Architectural Rule

> **Do not reverse this development order.**

---

# 40. Minimum Viable Product

The MVP must include:

* Procedural city
* Approximately 100 citizens
* Families
* Households
* Businesses
* Employment
* Basic economy
* Relationships
* Daily routines
* Event generation
* Kafka
* PostgreSQL
* Streamlit dashboard visualization

---

# 41. Advanced Showcase Features

Advanced features include:

* Snowflake
* Government AI
* Business AI
* Historian AI
* Deep citizen histories
* Life replay
* Causal graphs
* Disaster simulation
* Counterfactual timelines
* Timeline comparison
* Butterfly-effect experiments

---

# 42. Award-Worthy Showcase Scenario

The primary demonstration scenario should follow a single citizen and expand into a city-wide causal analysis.

## Step 1 — Meet Raj

Example profile:

```text
Name: Raj
Age: 42
Occupation: Engineer
Marital Status: Married
Children: 2
Savings: NPR 842,000
```

Show:

* Family
* Career
* Finances
* Relationships
* Routine
* Historical timeline

---

## Step 2 — Trigger Drought

The user triggers a drought.

---

## Step 3 — Observe the Cascade

```text
Drought
   |
   v
Food Shortage
   |
   v
Food Prices Increase
   |
   v
Household Expenses Increase
   |
   v
Business Costs Increase
   |
   v
Business Revenue Decreases
   |
   v
Raj Loses Job
```

---

## Step 4 — Ask Historian AI

User asks:

> Why did Raj become financially unstable?

The Historian Agent provides an evidence-backed explanation using the event history.

---

## Step 5 — Government AI Intervention

Government AI recommends a food subsidy.

Example evidence:

```text
Food Inflation: +37%
Household Stress: +21%
Unemployment: +7%
```

---

## Step 6 — Create Alternate Timeline

Create two branches:

```text
Timeline A
Food Subsidy
```

versus

```text
Timeline B
No Intervention
```

---

## Step 7 — Compare Outcomes

Compare:

* Wealth
* Employment
* Food prices
* Businesses
* Household stress
* Population

---

## Step 8 — Reveal the Butterfly Effect

Demonstrate how one city-wide policy can change individual lives.

```text
Government Policy
       |
       v
Food Prices
       |
       v
Business Costs
       |
       v
Employment
       |
       v
Household Income
       |
       v
Individual Life
```

---

# 43. Evaluation Criteria

## Simulation

Evaluate:

* Behavioral consistency
* Emergent behavior
* Citizen modeling depth

## Data Engineering

Evaluate:

* Event throughput
* Event integrity
* Kafka architecture
* PostgreSQL performance
* Snowflake analytical capability

## AI

Evaluate:

* Decision quality
* Evidence grounding
* Explainability
* Policy validation

## Experimentation

Evaluate:

* Reproducibility
* Counterfactual comparison
* Causal analysis

## Visualization

Evaluate:

* Usability
* Clarity
* Real-time interaction
* Historical exploration

---

# 44. Success Criteria

The system is successful when a user can:

1. Observe a living digital city.
2. Select any citizen.
3. Understand their current life.
4. Inspect their history.
5. Follow their relationships.
6. Understand their finances.
7. Observe events changing their life.
8. Trace why a major outcome occurred.
9. Ask an AI agent to explain the outcome.
10. Introduce a major event.
11. Allow the society to react.
12. Create an alternate timeline.
13. Compare outcomes.
14. Identify the causal differences between timelines.

---

# 45. Future Extensions

The following features are explicitly **out of scope** for the current project:

* Reinforcement learning
* Multi-agent LLM societies
* Advanced social psychology
* Knowledge graphs
* Graph databases
* PostGIS
* Flink
* Spark
* Iceberg
* Redis
* Distributed simulation
* Multiple cities
* Inter-city trade
* Multiple societies
* Political elections
* Cultural evolution
* Generational evolution

These may be considered in future versions.

---

# 46. Final Project Definition

**LIFE/100** is a deep digital society simulation consisting of approximately **100 persistent citizens** whose personal, social, economic, and historical lives are modeled at high resolution.

Every meaningful action generates an immutable event, creating a continuously evolving historical dataset.

Kafka provides the **event backbone**.

PostgreSQL maintains the **operational state**.

Snowflake provides the **analytical memory**.

AI agents analyze evidence and propose **constrained decisions**.

The Python Web Dashboard provides the **interactive interface** through which users can observe, investigate, manipulate, and experiment with the society.

> **The dashboard is the interface.**
> **The simulation is the world.**
> **The citizens are the data.**
> **Kafka is the nervous system.**
> **PostgreSQL is the current memory.**
> **Snowflake is the historical memory.**
> **AI agents are the decision-makers.**
> **The causal engine is the explanation layer.**
> **Alternate timelines are the experiments.**
>
> # Only 100 people. Every life matters.
