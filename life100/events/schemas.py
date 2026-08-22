"""Immutable event schema. SRS §14, §15.

Every meaningful state change in the simulation must be represented as one
of these events (CLAUDE.md ground rule 4/5). `event_id` is derived from the
simulation id/tick/sequence rather than a random UUID, so event identity
stays reproducible for the same seed/run — consistent with the project's
determinism rule (CLAUDE.md ground rule 8): nothing in the event schema
itself introduces unseeded randomness.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

EVENT_SCHEMA_VERSION = 1


class EventType(str, Enum):
    CITIZEN_BORN = "CITIZEN_BORN"
    CITIZEN_DIED = "CITIZEN_DIED"
    MARRIAGE = "MARRIAGE"
    DIVORCE = "DIVORCE"
    CHILD_BORN = "CHILD_BORN"
    MOVED = "MOVED"

    JOB_STARTED = "JOB_STARTED"
    JOB_LOST = "JOB_LOST"
    PROMOTION = "PROMOTION"
    SALARY_CHANGED = "SALARY_CHANGED"

    PURCHASE = "PURCHASE"
    SALE = "SALE"

    LOAN_CREATED = "LOAN_CREATED"
    LOAN_REPAID = "LOAN_REPAID"
    LOAN_DEFAULTED = "LOAN_DEFAULTED"

    BUSINESS_CREATED = "BUSINESS_CREATED"
    BUSINESS_EXPANDED = "BUSINESS_EXPANDED"
    BUSINESS_CONTRACTED = "BUSINESS_CONTRACTED"
    BUSINESS_FAILED = "BUSINESS_FAILED"

    PROPERTY_PURCHASED = "PROPERTY_PURCHASED"
    PROPERTY_SOLD = "PROPERTY_SOLD"

    MEDICAL_VISIT = "MEDICAL_VISIT"
    SCHOOL_ATTENDED = "SCHOOL_ATTENDED"

    RELATIONSHIP_CREATED = "RELATIONSHIP_CREATED"
    RELATIONSHIP_CHANGED = "RELATIONSHIP_CHANGED"
    RELATIONSHIP_ENDED = "RELATIONSHIP_ENDED"

    TAX_PAID = "TAX_PAID"
    POLICY_CHANGED = "POLICY_CHANGED"

    RESOURCE_EXTRACTED = "RESOURCE_EXTRACTED"

    DISASTER_STARTED = "DISASTER_STARTED"
    DISASTER_ENDED = "DISASTER_ENDED"

    PRICE_CHANGED = "PRICE_CHANGED"
    # Intentional schema extension beyond SRS §15's list, same precedent as
    # PRICE_CHANGED (CLAUDE.md rule 5): disease_outbreak needs a way to
    # represent a citizen falling ill that isn't MEDICAL_VISIT (a visit
    # improves health; this is the opposite — the shock that later prompts
    # a visit).
    HEALTH_IMPACTED = "HEALTH_IMPACTED"

    AI_DECISION_PROPOSED = "AI_DECISION_PROPOSED"
    AI_DECISION_ACCEPTED = "AI_DECISION_ACCEPTED"
    AI_DECISION_REJECTED = "AI_DECISION_REJECTED"


class Event(BaseModel):
    """The required fields exactly match SRS §14's example event."""

    event_id: str
    event_type: EventType
    schema_version: int = EVENT_SCHEMA_VERSION
    simulation_id: str
    simulation_tick: int
    simulation_time: str
    source_entity: str
    source_type: str
    city_id: str
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}
