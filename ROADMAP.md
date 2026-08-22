Save this as ROADMAP.md.

# LIFE/100 — Master Development Roadmap


**Project:** LIFE/100  
**Tagline:** Only 100 people. Every life matters.  
**Status:** Active Development  
**Language:** Python 3.11+  
**Development Model:** Incremental Vertical Slices  
**Total Milestones:** 30


---


## 1. Purpose


This document defines the complete development roadmap for LIFE/100.


Claude Code MUST use this document together with:


- `CLAUDE.md`
- `SRS.md`
- `PROGRESS.md`
- `WORKING_NOTES.md`


Each document has a specific responsibility:


| Document | Purpose |
|---|---|
| `SRS.md` | Authoritative system requirements |
| `CLAUDE.md` | Standing development rules and constraints |
| `ROADMAP.md` | Complete 30-step development plan |
| `PROGRESS.md` | What has already been completed |
| `WORKING_NOTES.md` | Current task breakdown and decisions |
| `ARCHITECTURE.md` | Architectural decisions and system structure |


The `SRS.md` is the authoritative specification.


The `ROADMAP.md` defines the sequence in which the system should be developed.


---


# 2. Critical Development Rule


The 30 roadmap steps are **major milestones**, not individual Claude Code sessions.


A milestone may require multiple sessions.


Claude Code MUST NOT attempt to implement an entire large milestone in one session.


For example:


```text
ROADMAP
    |
    +-- Step 14: Economy
            |
            +-- Session 1: Economic data models
            +-- Session 2: Household income
            +-- Session 3: Household expenses
            +-- Session 4: Business revenue
            +-- Session 5: Supply and demand
            +-- Session 6: Price calculation
            +-- Session 7: Loans and debt
            +-- Session 8: Economic integration
            +-- Session 9: Tests
            +-- Session 10: Review

The goal is to keep every Claude Code session:

small
testable
reviewable
reversible
within the current stage
3. Current Project Status

The project is currently at:

Phase 1 — World


Current Roadmap Step:
Step 3 — World Data Model

The initial repository foundation should be completed before beginning substantive simulation development.

The immediate development sequence is:

Step 1 — Project Foundation
Step 2 — Testing and Development Foundation
Step 3 — World Data Model
Step 4 — Deterministic Procedural World
Step 5 — Infrastructure and Buildings

Do not begin citizens, economy, events, Kafka, PostgreSQL, Snowflake, AI, or deployment before their respective roadmap stages are reached.

4. Technology Stack
4.1 Core Language
Python 3.11+
uv
dataclasses
Python type hints
Pytest
4.2 Simulation

The simulation engine will be implemented in Python.

The core simulation MUST use:

standard Python data structures
dataclasses
dictionaries
lists
sets
plain loops
explicit seeded random number generators

The simulation MUST NOT use:

pandas
numpy

for simulation state management.

4.3 Streaming

Primary:

Apache Kafka

Local lightweight alternative:

Redpanda

Redpanda may be used during development because it provides Kafka-compatible APIs.

4.4 Operational Database
PostgreSQL

PostgreSQL stores the current operational state of the simulation.

4.5 Analytical Warehouse
Snowflake

A local analytical stand-in may be used during development if required.

Snowflake should only be introduced when the roadmap reaches the analytics stage.

4.6 Dashboard
Streamlit

The dashboard is a user interface.

The dashboard MUST NOT become the simulation engine.

4.7 AI
Google Gemini API (Flash, free tier)
`google-genai` SDK

Note: the original spec called for the Anthropic API. For the 2-day
certificate submission this was switched to Gemini Flash (free tier) — see
`SCOPE.md` for the reasoning. The architecture (agent proposes, validator
checks, engine applies) is unchanged; only the LLM provider differs.

Important distinction:

Claude Code
    =
Development Assistant


Gemini API
    =
Runtime AI used by LIFE/100

Claude Code is used to develop LIFE/100.

The actual LIFE/100 AI agents must call the Gemini API directly.

4.8 Infrastructure
Docker
Docker Compose

Docker will be introduced progressively and finalized during the deployment phase.

4.9 Version Control
Git
GitHub
5. Target Architecture

The final architecture should generally follow this structure:

                           USER
                            |
                            v
                  +-------------------+
                  | Streamlit         |
                  | Dashboard         |
                  +---------+---------+
                            |
                            v
                  +-------------------+
                  | API / Application |
                  | Layer             |
                  +---------+---------+
                            |
                            v
                  +-------------------+
                  | Simulation Engine |
                  +---------+---------+
                            |
                            v
                    Event Interface
                            |
                            v
                         Kafka
                    /       |       \
                   /        |        \
                  v         v         v
          PostgreSQL     Consumers   AI Events
          Current State     |           |
                            v           |
                        Snowflake       |
                         History        |
                                        |
                                        v
                              +----------------+
                              | Gemini API     |
                              +-------+--------+
                                      |
                                      v
                               Proposed Action
                                      |
                                      v
                               Action Validator
                                      |
                                      v
                              Simulation Engine
                                      |
                                      v
                                 World State
                                      |
                                      v
                                    Event

This architecture is developed incrementally.

Do not create the entire architecture during the early stages.

6. Core Development Principles
6.1 Depth Over Scale

The population is intentionally limited to approximately 100 citizens.

The project prioritizes:

individual depth
personal history
relationships
economics
decision-making
events
causal effects
historical traceability

The project does not prioritize population scale.

6.2 Determinism

Simulation behavior should be reproducible whenever practical.

A simulation should be identifiable through:

Simulation ID
+
Random Seed
+
Initial Configuration
+
Simulation Version
+
AI Model Version
+
Agent Configuration

Avoid uncontrolled randomness.

Do not use:

random.random()

without a controlled RNG.

Prefer:

rng = random.Random(seed)

and pass the RNG explicitly where required.

6.3 Events Are the Source of Truth

Once the event system is implemented, meaningful state changes MUST pass through the event architecture.

Do not directly mutate important simulation state without producing the appropriate event.

Bad:

citizen.money -= 500

Preferred:

Decision
    |
    v
Event
    |
    v
Validation
    |
    v
Event Application
    |
    v
State Change
6.4 AI Never Directly Modifies State

AI agents can:

observe
analyze
reason
propose
explain

AI agents cannot directly modify simulation state.

Required architecture:

AI Agent
    |
    v
Proposed Decision
    |
    v
Policy / Action Validator
    |
    v
Simulation Engine
    |
    v
World State Change
    |
    v
Event
6.5 Kafka Must Not Block Simulation

The simulation must not stop because Kafka is unavailable.

Use an event interface or abstraction.

The simulation should produce events without being tightly coupled to the Kafka transport implementation.

6.6 Snowflake Must Not Be on the Critical Path

Snowflake is an analytical system.

The simulation MUST continue operating if Snowflake becomes temporarily unavailable.

The simulation must never require Snowflake to advance simulation time.

6.7 No Premature Optimization

Do not introduce technologies simply because they may be useful later.

Explicitly avoid premature introduction of:

NumPy
Pandas
Spark
Flink
Redis
Graph databases
Kubernetes
distributed simulation

unless the scope is explicitly changed.

7. Roadmap Overview

The complete development process consists of 30 major milestones.

Phase	Steps	Area
Phase 0	1–2	Foundation
Phase 1	3–5	World
Phase 2	6–8	Citizens and Society
Phase 3	9–11	Daily Life
Phase 4	12–14	Economy
Phase 5	15–16	Events
Phase 6	17	Streaming
Phase 7	18–19	PostgreSQL
Phase 8	20–22	Dashboard
Phase 9	23–24	Analytics
Phase 10	25–26	AI
Phase 11	27–28	Explainability
Phase 12	29	Experimentation
Phase 13	30	Deployment
Phase 0 — Foundation
Step 1 — Project Foundation
SRS References
SRS §38
SRS §39
Objective

Create the initial Python repository and development environment.

Tasks

Implement:

Python 3.11+
uv
pyproject.toml
Git repository
.gitignore
.env.example
configuration system
logging foundation
basic package structure
Required Files
CLAUDE.md
SRS.md
ROADMAP.md
PROGRESS.md
WORKING_NOTES.md
pyproject.toml
.env.example
.gitignore
Required Commands

The following must work:

uv run python --version

and:

uv run pytest
Out of Scope

Do not implement:

Kafka
PostgreSQL
Snowflake
AI
Streamlit
Citizens
Economy
Completion Criteria

The repository can be cloned and initialized cleanly.

Step 2 — Testing and Development Foundation
Objective

Establish reliable development conventions before implementing the simulation.

Tasks

Implement:

Pytest structure
test conventions
deterministic RNG utility
configuration loading
logging conventions
type checking configuration
linting configuration
basic CI workflow
Deterministic RNG

Provide a controlled mechanism for seeded randomness.

Example:

import random


rng = random.Random(seed)
Completion Criteria

The following command works:

uv run pytest

All tests pass.

Phase 1 — World
Step 3 — World Data Model
SRS References
SRS §7
Objective

Create the foundational World model.

Implement

Create models for:

World
WorldConfig
coordinates
dimensions
terrain representation
seed
world metadata

Use:

dataclasses
strict typing
simple Python structures
Requirements

The world must accept:

seed
+
configuration

and produce a deterministic world representation.

Tests

Test:

World creation.
Configuration validation.
World dimensions.
Seed persistence.
Deterministic equality.
Completion Criteria

A minimal World can be created without the dashboard.

Step 4 — Deterministic Procedural World Generation
SRS References
SRS §7
Objective

Generate the basic city environment.

Implement

Generate:

terrain
residential zones
commercial zones
industrial zones
roads
natural resources
Deterministic Requirement

Given the same seed and configuration:

seed = 847291

the generated world must be identical.

Example test:

world_a = generate_world(seed=847291)
world_b = generate_world(seed=847291)


assert world_a == world_b

Different seeds should be capable of producing different worlds.

Completion Criteria

A deterministic procedural city environment exists.

Step 5 — Infrastructure and Buildings
SRS References
SRS §6
SRS §7
Objective

Populate the generated world with usable infrastructure.

Implement

Generate:

homes
schools
hospitals
shops
factories
banks
government buildings
parks
utilities
other required infrastructure
Requirements

Buildings must belong to the world model and have stable identifiers.

Completion Criteria

The generated world represents a small functioning city environment.

Phase 2 — Citizens and Society
Step 6 — Citizen Model
SRS References
SRS §6.1
Objective

Create the deeply modeled Citizen entity.

Identity

Implement:

citizen ID
name
age
date of birth
gender
nationality
home
Education

Implement:

education level
school
university
skills
academic performance
Employment

Implement:

occupation
employer
salary
employment history
experience
job satisfaction
Financial

Implement:

income
savings
debt
assets
credit score
expenses
investments
Health

Implement:

health score
fitness
stress
sleep
medical history
healthcare usage
Psychological

Implement:

personality traits
risk tolerance
ambition
patience
social tendency
decision preferences
Goals

Implement:

career goals
financial goals
family goals
personal goals
long-term aspirations
Completion Criteria

A citizen can exist as a complete domain entity.

Step 7 — Families and Households
SRS References
SRS §6.2
SRS §6.3
Objective

Create family and household structures.

Implement

Families must support:

parents
children
siblings
spouses
partners

Households must support:

members
property
income
expenses
savings
debt
assets
goals
financial stress
living conditions
Population

Generate approximately:

100 citizens

with coherent household structures.

Completion Criteria

The population has realistic family and household relationships.

Step 8 — Social Relationships
SRS References
SRS §12
Objective

Create a dynamic social network.

Relationship Properties

Each relationship may contain:

type
strength
trust
frequency
history
last interaction
Relationship Types

Support:

family
friend
coworker
neighbor
teacher
employer
Example
Raj
 |
 +-- Maya   -> Spouse      -> Strength: 0.94
 +-- John   -> Friend      -> Strength: 0.78
 +-- David  -> Coworker    -> Strength: 0.62
 +-- Sarah  -> Neighbor    -> Strength: 0.31
Completion Criteria

Citizens can form, maintain, change, and end relationships.

Phase 3 — Daily Life
Step 9 — Simulation Clock
SRS References
SRS §9
Objective

Implement simulation time.

Required Time Units
sim_tick
sim_hour
sim_day
sim_month
sim_year
Controls

The engine must eventually support:

pause
resume
step
x1
x10
x100
x1000
Rule

Simulation time is the absolute source of truth.

Wall-clock time must not determine simulation history.

Completion Criteria

The simulation can advance deterministically through simulated time.

Step 10 — Daily Routines
SRS References
SRS §10
Objective

Give citizens dynamic daily lives.

Implement

Possible activities include:

waking
breakfast
commuting
working
lunch
school
shopping
recreation
social interaction
family time
sleeping
Routines Must Respond To
employment
health
family
weather
income
stress
goals
unexpected events
Completion Criteria

Citizens perform meaningful daily activities.

Step 11 — Citizen Decision Engine
SRS References
SRS §11
Objective

Implement deterministic low-level citizen decisions.

Decisions

Support decisions such as:

purchase food
go to work
change jobs
save money
take a loan
visit hospital
attend school
socialize
start basic activities
travel
recreation
AI Rule

Do not use Gemini (or any LLM) for ordinary low-level decisions.

These decisions should primarily be handled by deterministic simulation logic.

Completion Criteria

Citizens make repeatable, context-sensitive day-to-day decisions.

Phase 4 — Economy
Step 12 — Employment and Income
SRS References
SRS §6.1
SRS §13
Objective

Create the employment system.

Implement
jobs
employers
hiring
firing
salaries
promotions
salary changes
employment history
job satisfaction
Completion Criteria

Citizens can earn income through employment.

Step 13 — Businesses and Production
SRS References
SRS §6.4
SRS §13
Objective

Create functioning businesses.

Business Attributes

Implement:

business ID
industry
owner
employees
revenue
expenses
profit
cash
inventory
debt
customers
products
location
Business Actions

Support:

hire
fire
produce
sell
purchase
borrow
invest
expand
contract
fail
Completion Criteria

Businesses interact with citizens and households.

Step 14 — Basic Economic System
SRS References
SRS §13
Objective

Create the core economic feedback loop.

Implement
consumption
supply
demand
prices
production
inventory
savings
debt
loans
taxes
household expenses
investments
Example Feedback Loop
Food Demand Increases
        |
        v
Inventory Decreases
        |
        v
Food Price Increases
        |
        v
Household Expenses Increase
        |
        v
Savings Decrease
Completion Criteria

The simulation has a functioning basic economy.

Phase 5 — Events
Step 15 — Event Architecture
SRS References
SRS §14
SRS §15
Objective

Create the immutable event system.

Required Event Fields

Every meaningful event must contain:

event_id
event_type
schema_version
simulation_id
simulation_tick
simulation_time
source_entity
source_type
city_id
payload
Implement
base event model
event IDs
event schemas
schema versions
event validation
serialization
deserialization
Event Types

Support the SRS-defined event types:

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
Completion Criteria

Meaningful simulation actions can produce validated immutable events.

Step 16 — Event-Driven State Changes
Objective

Make events the formal state-change boundary.

Required Flow
Action
    |
    v
Event Creation
    |
    v
Event Validation
    |
    v
Event Application
    |
    v
State Change
Implement
event producers
event validators
event application
duplicate detection
idempotency
event history
replay capability
Completion Criteria

Important state changes can be traced back to events.

Phase 6 — Streaming
Step 17 — Kafka / Redpanda Integration
SRS References
SRS §16
Objective

Introduce the event streaming infrastructure.

Topics

Create:

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
Implement
producers
consumers
serialization
topic configuration
retry handling
error handling
consumer management
basic monitoring
Critical Requirement

The simulation MUST NOT block while waiting for Kafka.

Required architecture:

Simulation Engine
        |
        v
Event Interface
        |
        v
Kafka Producer
Completion Criteria

Events can flow reliably from the simulation into Kafka and consumers can process them.

Phase 7 — PostgreSQL
Step 18 — Operational Database
SRS References
SRS §17
Objective

Introduce PostgreSQL as the current-state operational database.

Tables

Implement the necessary operational structures, including:

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
Completion Criteria

PostgreSQL can represent the current operational state of the simulation.

Step 19 — State Synchronization and Recovery
Objective

Make operational persistence reliable.

Implement
Kafka-to-PostgreSQL consumers
idempotency
checkpoints
restart recovery
duplicate-event handling
malformed-event handling
database failure handling
state reconstruction
Completion Criteria

The simulation can restart without corrupting operational state.

Phase 8 — Dashboard
Step 20 — Streamlit Dashboard Foundation
SRS References
SRS §30
SRS §31
SRS §32
Objective

Create the browser-based user interface.

Implement
Streamlit application
simulation status
simulation clock
start
pause
resume
step
speed controls
basic system status
Architecture Rule

The dashboard MUST NOT become the simulation engine.

Completion Criteria

A user can control and observe the simulation through a browser.

Step 21 — World and Entity Visualization
Objective

Create the main exploration interface.

World View

Display:

city
homes
roads
businesses
schools
hospitals
citizens
Citizen View

Display:

identity
family
employment
finance
health
relationships
goals
current activity
Household View

Display:

members
income
expenses
assets
debt
stress
history
Business View

Display:

employees
revenue
costs
inventory
profit
history
Completion Criteria

Users can inspect individual lives and organizations.

Step 22 — Live Events and Dashboard Analytics
Objective

Create a live analytical interface.

Metrics

Display:

population
GDP
inflation
employment
average wealth
migration
business activity
event rate
simulation ticks per second
Kafka lag
database latency
Visualization Modes

Implement:

Human
Economic
Social
Environmental
Causal
Historical
Live Event Feed

Provide an event stream showing meaningful events as the simulation progresses.

Completion Criteria

The dashboard provides a live overview of the digital society.

Phase 9 — Analytics
Step 23 — Analytical Data Pipeline
SRS References
SRS §18
SRS §19
Objective

Create the historical analytical pipeline.

Architecture
Kafka
    |
    v
Analytical Consumers
    |
    v
Historical Data
    |
    v
Snowflake
Important Requirement

Snowflake MUST NOT be part of the simulation's critical execution path.

Fact Tables

Implement:

fact_transactions
fact_employment
fact_citizen_events
fact_household_finance
fact_business_activity
fact_relationship_events
fact_policy_effects
fact_health_events
Dimensions

Implement:

dim_citizen
dim_household
dim_family
dim_business
dim_city
dim_date
dim_location
dim_product
Completion Criteria

Historical simulation data is available in the analytical warehouse.

Step 24 — Historical Analytics
Objective

Create analytical capabilities over the accumulated simulation history.

Analytics

Support analysis of:

citizen life history
household finances
employment history
economic activity
business performance
relationship changes
migration patterns
wealth distribution
health trends
policy effects
disaster impact
decision history
Completion Criteria

Users can investigate historical society behavior rather than only current state.

Phase 10 — AI
Step 25 — Gemini API Foundation
SRS References
SRS §20
SRS §21
Objective

Integrate the runtime Gemini API (switched from the originally specified
Anthropic API for the certificate submission — free-tier provider; see
SCOPE.md).

Important Distinction
Claude Code
    |
    +-- Development tool


Gemini API
    |
    +-- LIFE/100 runtime AI

The runtime AI must use the Gemini API directly.

Configuration

Use environment variables:

GEMINI_API_KEY
GEMINI_MODEL

Never hardcode credentials.

Implement
Gemini API client (google-genai SDK)
model configuration
structured requests
structured responses
timeout handling
retry/backoff handling (free-tier rate limits)
API error handling
AI logging
model version tracking
agent configuration tracking
AI Response Requirements

AI responses should use structured outputs wherever practical so that application code can validate them.

AI responses MUST NOT directly modify simulation state.

Completion Criteria

LIFE/100 can successfully call the Gemini API and receive a structured response.

Step 26 — AI Agents and Safety Boundary
SRS References
SRS §20
SRS §21
Objective

Implement constrained AI decision-making.

Government Agent

Analyze:

inflation
unemployment
food prices
household stress
business failures
tax revenue
economic growth

Propose:

tax changes
subsidies
interest-rate changes
government spending
emergency policies
Business Agent

Analyze:

demand
revenue
inventory
costs
competition
employees
loans

Propose:

hiring
firing
pricing
production changes
expansion
loans
Household Decision Agent

Activate for significant decisions such as:

major job opportunities
moving house
major loans
education
business investment
major financial decisions
Historian Agent

Answer historical questions using actual simulation evidence.

Example:

Why did Raj become unemployed?

The Historian Agent must retrieve relevant events before generating the explanation.

It must not fabricate historical evidence.

AI Safety Boundary

The following architecture is mandatory:

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
Event

The AI agent cannot bypass the validator.

Completion Criteria

AI agents can reason about the simulation and propose decisions without directly controlling simulation state.

Phase 11 — Explainability
Step 27 — Historian and Life Replay
SRS References
SRS §24
SRS §25
Objective

Create complete citizen histories.

Implement
citizen timeline
life replay
significant memories
historical event retrieval
evidence retrieval
Historian Agent integration
Example Timeline
Birth
  |
  v
School
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
Business
  |
  v
Current State
Memory System

Store significant events such as:

first job
marriage
birth of child
major financial loss
death of family member
business failure
major achievement
Completion Criteria

Every citizen has a navigable and replayable historical life.

Step 28 — Causal Analysis
SRS References
SRS §22
SRS §23
Objective

Create an explainability and causal-tracing system.

Example
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
The System Must Answer
What happened?
Why did it happen?
What caused it?
Who was affected?
What happened afterward?
Dashboard

Provide interactive causal-chain visualization.

Completion Criteria

Major state changes have navigable explanation paths.

Phase 12 — Experimentation
Step 29 — Disasters and Alternate Timelines
SRS References
SRS §26
SRS §27
SRS §28
SRS §29
Objective

Allow users to manipulate the world and perform controlled experiments.

Disaster System

Implement:

drought
flood
earthquake
disease outbreak
economic recession
food shortage
energy crisis
Example
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
Business Profit Decreases
    |
    v
Layoffs
    |
    v
Unemployment Increases
Alternate History

Allow users to branch from an existing simulation state.

Branch Metadata

Record:

parent simulation
branch point
original seed
initial configuration
policy differences
simulation version
AI model version
agent configuration
Architecture
Original Simulation
        |
        v
   Branch Point
      /     \
     /       \
    v         v
Timeline A  Timeline B
    |         |
    v         v
 Simulate   Simulate
     \       /
      \     /
       v   v
      Compare
Timeline Comparison

Compare:

Metric	Timeline A	Timeline B
Population	...	...
Food Price	...	...
Unemployment	...	...
Average Wealth	...	...
Business Count	...	...
Household Stress	...	...
Butterfly Effect Analysis

Trace small changes into downstream effects.

Example:

Citizen spends NPR 500 instead of NPR 300
        |
        v
Business Revenue Changes
        |
        v
Inventory Changes
        |
        v
Production Changes
        |
        v
Employment Changes
        |
        v
Household Income Changes
        |
        v
Economic and Social Consequences
Completion Criteria

Users can:

Branch a simulation.
Change conditions.
Run the alternate timeline.
Compare outcomes.
Identify the events that caused divergence.
Phase 13 — Production
Step 30 — Dockerization and Deployment
Objective

Make LIFE/100 reproducibly deployable.

Dockerize

Create containers for appropriate services, including:

simulation
dashboard
workers/consumers
PostgreSQL
Kafka/Redpanda
Required Files
Dockerfile
docker-compose.yml
.env.example

Additional Dockerfiles may be created for separate services where appropriate.

Environment Variables

Use environment variables for:

DATABASE_URL
KAFKA_BROKER
GEMINI_API_KEY
GEMINI_MODEL
SNOWFLAKE_ACCOUNT
SNOWFLAKE_USER
SNOWFLAKE_PASSWORD

Never hardcode credentials.

Production Requirements

Implement:

production Docker images
health checks
database migrations
persistent storage
logging
error handling
environment configuration
secret management
restart policies
resource configuration
monitoring
Deployment

Deploy LIFE/100 to an appropriate hosting or cloud environment.

The final deployment should provide access to the Streamlit dashboard.

Completion Criteria

LIFE/100 can:

Run locally with Docker Compose.
Start required services.
Persist required data.
Recover from service restarts.
Use environment-based configuration.
Connect to the Gemini API.
Run the simulation.
Display the dashboard.
Be deployed to a production environment.
8. Final Architecture

At completion, the system should resemble:

                              USER
                               |
                               v
                    +---------------------+
                    | Streamlit Dashboard |
                    +----------+----------+
                               |
                               v
                    +---------------------+
                    | API / Application   |
                    | Layer               |
                    +----------+----------+
                               |
                               v
                    +---------------------+
                    | Simulation Engine   |
                    +----------+----------+
                               |
                               v
                       Event Interface
                               |
                               v
                            Kafka
                       /       |       \
                      /        |        \
                     v         v         v
             PostgreSQL   Consumers   AI Events
             Current State    |           |
                              v           |
                          Snowflake       |
                           History        |
                                          |
                                          v
                                +----------------+
                                | Gemini API     |
                                +-------+--------+
                                        |
                                        v
                                 Proposed Action
                                        |
                                        v
                                 Action Validator
                                        |
                                        v
                                Simulation Engine
                                        |
                                        v
                                   World State
                                        |
                                        v
                                      Event
9. Final Demonstration Scenario

The final project should demonstrate the complete LIFE/100 concept through one compelling scenario.

9.1 Introduce Raj

Create or identify a citizen:

Name: Raj
Age: 42
Occupation: Engineer
Marital Status: Married
Children: 2
Savings: NPR 842,000
9.2 Explore Raj's Life

Display:

family
career
finances
relationships
health
daily routine
historical timeline
memories
9.3 Trigger a Drought

The user triggers:

DROUGHT
9.4 Observe Emergent Effects

The system should produce a chain similar to:

Drought
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
Household Expenses Increase
    |
    v
Business Costs Increase
    |
    v
Business Profit Decreases
    |
    v
Layoffs
    |
    v
Raj Loses Job
    |
    v
Raj Income Decreases
    |
    v
Raj Savings Decrease
    |
    v
Raj Financial Stress Increases

The result must emerge from the simulation.

It must NOT be hardcoded as:

if drought:
    raj.lose_job()
10. Historian Demonstration

The user asks:

Why did Raj become financially unstable?

The Historian Agent should:

Retrieve relevant events.
Trace the causal chain.
Identify affected entities.
Build an evidence-backed explanation.
Provide the explanation through the dashboard.

The AI must not invent events.

11. Government AI Demonstration

The Government Agent analyzes:

food inflation
unemployment
household stress
business failures
tax revenue

It proposes:

Food Subsidy

with evidence.

The proposal becomes:

Government Agent
        |
        v
Food Subsidy Proposal
        |
        v
Policy Validator
        |
        v
Approved
        |
        v
Simulation Engine
        |
        v
POLICY_CHANGED Event
12. Alternate Timeline Demonstration

Create two timelines.

Timeline A
No Government Intervention
Timeline B
Food Subsidy Implemented

Run both simulations from the same branch point.

13. Timeline Comparison

Compare:

Metric	Subsidy	No Action
Population	...	...
Food Price	...	...
Unemployment	...	...
Average Wealth	...	...
Business Count	...	...
Household Stress	...	...

The system should identify the events that caused the divergence.

14. Butterfly Effect Demonstration

Demonstrate how a high-level policy decision can affect individual citizens.

Example:

Government Policy
        |
        v
Food Prices
        |
        v
Household Expenses
        |
        v
Business Costs
        |
        v
Employment
        |
        v
Citizen Income
        |
        v
Citizen Wealth
        |
        v
Citizen Decisions
        |
        v
Social Consequences

This is the core showcase of LIFE/100.

15. Final Completion Checklist
15.1 Simulation
 Deterministic world generation
 Approximately 100 citizens
 Families
 Households
 Relationships
 Daily routines
 Citizen decisions
 Employment
 Businesses
 Economy
 Government
 Environment
15.2 Event System
 Immutable event model
 Event validation
 Event schema versioning
 Event history
 Event replay
 Event-driven state changes
 Duplicate-event handling
 Idempotency
15.3 Streaming
 Kafka or Redpanda
 Producers
 Consumers
 Topics
 Serialization
 Retry handling
 Error handling
 Recovery
 Monitoring
15.4 PostgreSQL
 PostgreSQL integration
 Operational schema
 Current state
 Migrations
 Idempotency
 Recovery
 State reconstruction
15.5 Snowflake
 Historical pipeline
 Fact tables
 Dimension tables
 Analytical queries
 Historical citizen data
 Economic analytics
 Policy analytics
 Disaster analytics
15.6 Dashboard
 World View
 Citizen View
 Household View
 Business View
 City Dashboard
 Simulation controls
 Live event stream
 Historical view
 Causal visualization
 AI chat
 Timeline comparison
15.7 AI
 Gemini API
 Gemini integration
 Government Agent
 Business Agent
 Household Decision Agent
 Historian Agent
 Structured AI outputs
 AI decision validation
 Evidence grounding
 AI decision events
 AI model version tracking
 AI error handling
15.8 Explainability
 Citizen life replay
 Citizen memories
 Historical event retrieval
 Evidence-backed explanations
 Causal chains
 Causal graph visualization
 Cause-and-effect tracing
15.9 Experimentation
 Drought
 Flood
 Earthquake
 Disease outbreak
 Economic recession
 Food shortage
 Energy crisis
 Simulation branching
 Alternate timelines
 Timeline comparison
 Divergence analysis
 Butterfly-effect analysis
15.10 Deployment
 Docker
 Docker Compose
 Environment configuration
 Secret management
 Health checks
 Persistent storage
 Database migrations
 Service recovery
 Production configuration
 Monitoring
 Deployment
 Public dashboard
16. Rules for Claude Code

Claude Code MUST follow these rules during every session.

16.1 Before Starting

Claude Code MUST:

Read CLAUDE.md.
Read the relevant section of SRS.md.
Read PROGRESS.md.
Read WORKING_NOTES.md.
Identify the current roadmap step.
Identify the smallest unfinished task.
16.2 During Development

Claude Code MUST:

Work only on the current roadmap step.
Avoid implementing future stages.
Keep the task small.
Write tests.
Preserve existing functionality.
Follow the SRS.
Follow CLAUDE.md.
Avoid unnecessary dependencies.
Avoid premature optimization.
Maintain deterministic behavior where required.
16.3 After Development

Claude Code MUST:

Run tests.
Review the changes.
Update PROGRESS.md.
Update WORKING_NOTES.md if decisions were made.
Explain what was completed.
Explain what should happen next.
Commit completed work when appropriate.
17. Session Scope Rule

Claude Code should not interpret a roadmap step as one session.

For example:

Current Step:
Step 14 — Economy

Claude should NOT automatically implement:

employment
businesses
pricing
loans
taxes
investments
economic analytics

in one session.

Instead:

Step 14 — Economy


Current small task:
Implement household expense calculation.


Implement:
    Household expense model
    Expense calculation
    Unit tests


Then:
    Update PROGRESS.md
    Stop

The next session can implement the next small task.

18. Definition of Done

A task is complete only when:

 Implementation exists.
 Unit tests exist.
 Tests pass.
 Existing tests still pass.
 Code is appropriately typed.
 No unnecessary dependency was introduced.
 SRS requirements are respected.
 PROGRESS.md is updated.
 WORKING_NOTES.md is updated when required.
 No future scope was implemented.
 The change is reviewable.
19. Git Discipline

After completing a small task, Claude Code should perform:

git status
git diff
uv run pytest

Then commit the completed work.

Use descriptive commit messages.

Examples:

feat(world): add World data model (SRS §7)


feat(world): add deterministic terrain generation (SRS §7)


feat(citizens): add Citizen entity model (SRS §6.1)


feat(events): add immutable event schema (SRS §14)


feat(streaming): add Kafka event producer (SRS §16)


feat(database): add PostgreSQL operational schema (SRS §17)


feat(ai): integrate Gemini API client (SRS §20)


feat(ai): add government decision agent (SRS §20)

Avoid giant commits containing an entire phase.

20. Scope Protection

The following technologies and features are explicitly outside the current scope unless the project requirements are intentionally changed.

Game Engines
Godot
Unity
Unreal Engine

LIFE/100 is a Python-native simulation.

Data Processing

Do not introduce:

NumPy for simulation state
Pandas for simulation state
Spark
Flink

unless explicitly justified later.

Infrastructure

Do not introduce:

Redis
Kubernetes
distributed simulation
complex service meshes

without a demonstrated requirement.

Advanced AI

Currently out of scope:

reinforcement learning
multi-agent LLM societies
fully LLM-controlled citizens
autonomous LLM citizen behavior

Gemini (the runtime AI) should be used selectively for:

strategic decisions
policy reasoning
business decisions
significant household decisions
historical reasoning
Advanced Data Architecture

Currently out of scope:

graph databases
PostGIS
Apache Iceberg
multiple cities
inter-city trade
multiple societies
political elections
cultural evolution
21. Final Project Definition

LIFE/100 is a deep digital society simulation containing approximately 100 persistent citizens whose personal, social, economic, and historical lives are modeled at high resolution.

Every meaningful action generates an immutable event.

Kafka provides event transport.

PostgreSQL maintains current operational state.

Snowflake provides historical analytical memory.

Gemini-backed agents analyze evidence and propose constrained decisions.

The simulation engine remains the authority over world state.

The Streamlit dashboard allows users to observe, investigate, replay, manipulate, and experiment with the society.

The complete system should demonstrate:

Living Society
      |
      v
Individual Lives
      |
      v
Interactions
      |
      v
Emergent Outcomes
      |
      v
Immutable Events
      |
      v
Historical Data
      |
      v
AI Reasoning
      |
      v
Causal Explanation
      |
      v
Controlled Intervention
      |
      v
Alternate Timeline
      |
      v
Experimental Comparison
22. Project Philosophy

The dashboard is the interface.

The simulation is the world.

The citizens are the data.

Kafka is the nervous system.

PostgreSQL is the current memory.

Snowflake is the historical memory.

Gemini is the reasoning layer.

The causal engine is the explanation layer.

Alternate timelines are the experiments.