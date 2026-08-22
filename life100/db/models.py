"""PostgreSQL operational schema. SRS §17.

A deliberately small subset of the SRS's full table list (citizens,
households, businesses, events, simulation_state) — enough to demonstrate
the operational-state pattern for this submission; see SCOPE.md. `events`
is the durable, append-only event log (mirrors `life100.events.store.EventLog`
but survives process restarts) and is what the DuckDB warehouse pipeline
reads from.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CitizenRow(Base):
    __tablename__ = "citizens"

    citizen_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String)
    household_id: Mapped[str | None] = mapped_column(String, nullable=True)
    occupation: Mapped[str] = mapped_column(String, default="unemployed")
    employer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    salary: Mapped[float] = mapped_column(Float, default=0.0)
    savings: Mapped[float] = mapped_column(Float, default=0.0)
    debt: Mapped[float] = mapped_column(Float, default=0.0)
    health_score: Mapped[float] = mapped_column(Float, default=0.8)
    stress: Mapped[float] = mapped_column(Float, default=0.2)
    alive: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class HouseholdRow(Base):
    __tablename__ = "households"

    household_id: Mapped[str] = mapped_column(String, primary_key=True)
    member_ids: Mapped[list] = mapped_column(JSON, default=list)
    income: Mapped[float] = mapped_column(Float, default=0.0)
    expenses: Mapped[float] = mapped_column(Float, default=0.0)
    savings: Mapped[float] = mapped_column(Float, default=0.0)
    debt: Mapped[float] = mapped_column(Float, default=0.0)
    financial_stress: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BusinessRow(Base):
    __tablename__ = "businesses"

    business_id: Mapped[str] = mapped_column(String, primary_key=True)
    industry: Mapped[str] = mapped_column(String)
    building_id: Mapped[str] = mapped_column(String)
    employee_ids: Mapped[list] = mapped_column(JSON, default=list)
    cash: Mapped[float] = mapped_column(Float, default=0.0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    expenses: Mapped[float] = mapped_column(Float, default=0.0)
    profit: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventRow(Base):
    """Append-only event log — the durable counterpart to
    `life100.events.store.EventLog`. Primary key on `event_id` gives the
    consumer idempotent inserts for free (SRS §16/§19 duplicate handling)."""

    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    simulation_id: Mapped[str] = mapped_column(String, index=True)
    simulation_tick: Mapped[int] = mapped_column(Integer)
    simulation_time: Mapped[str] = mapped_column(String)
    source_entity: Mapped[str] = mapped_column(String, index=True)
    source_type: Mapped[str] = mapped_column(String)
    city_id: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SimulationStateRow(Base):
    __tablename__ = "simulation_state"

    simulation_id: Mapped[str] = mapped_column(String, primary_key=True)
    seed: Mapped[int] = mapped_column(Integer)
    tick: Mapped[int] = mapped_column(Integer, default=0)
    food_price_index: Mapped[float] = mapped_column(Float, default=1.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RelationshipRow(Base):
    """SRS §17's named `relationships` table — the social graph
    (simulation/social.py's `Relationship`), persisted so it's queryable
    independent of the in-memory engine."""

    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[str] = mapped_column(String, index=True)
    citizen_id: Mapped[str] = mapped_column(String, index=True)
    other_id: Mapped[str] = mapped_column(String, index=True)
    relationship_type: Mapped[str] = mapped_column(String)
    strength: Mapped[float] = mapped_column(Float)
    trust: Mapped[float] = mapped_column(Float)
    frequency: Mapped[float] = mapped_column(Float)


class GovernmentRow(Base):
    """SRS §17's named `government` table (simulation/government.py's
    `Government` — the structured policy levers, one row per simulation)."""

    __tablename__ = "government"

    simulation_id: Mapped[str] = mapped_column(String, primary_key=True)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.15)
    interest_rate: Mapped[float] = mapped_column(Float, default=0.05)
    food_subsidy: Mapped[float] = mapped_column(Float, default=0.0)
    healthcare_spending: Mapped[float] = mapped_column(Float, default=0.0)
    education_spending: Mapped[float] = mapped_column(Float, default=0.0)
    infrastructure_spending: Mapped[float] = mapped_column(Float, default=0.0)
    business_regulation: Mapped[float] = mapped_column(Float, default=0.3)
    environmental_regulation: Mapped[float] = mapped_column(Float, default=0.3)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InfrastructureRow(Base):
    """SRS §17's named `infrastructure`/`locations` tables (world.py's
    `Building` — homes/schools/hospitals/shops/factories/banks/government
    buildings, with their (x, y) location)."""

    __tablename__ = "infrastructure"

    building_id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, index=True)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    city_id: Mapped[str] = mapped_column(String, index=True)


class AgentRow(Base):
    """SRS §17's named `agents` table — a record of each AI agent's
    configuration (SRS §35 reproducibility: agent configuration + model
    version)."""

    __tablename__ = "agents"

    agent_name: Mapped[str] = mapped_column(String, primary_key=True)
    model: Mapped[str] = mapped_column(String)
    module_path: Mapped[str] = mapped_column(String)
    last_active_tick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
