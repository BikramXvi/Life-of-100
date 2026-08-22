"""The AI safety boundary. SRS §21.

This is the *only* thing standing between an AI agent's proposal and the
simulation engine. No agent module calls `engine.emit(POLICY_CHANGED, ...)`
directly — it only ever happens after a proposal passes through here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# action -> (min, max) allowed value range
ALLOWED_POLICY_ACTIONS: dict[str, tuple[float, float]] = {
    "food_subsidy": (0.0, 1.0),
    "tax_rate": (0.0, 0.6),
    "interest_rate": (0.0, 0.3),
}
BUSINESS_ACTION_BOUNDS: dict[str, tuple[float, float]] = {
    "hire": (1, 5),
    "fire": (1, 5),
    "expand": (500, 20_000),
    "contract": (0.05, 0.5),
    "take_loan": (500, 20_000),
}
HOUSEHOLD_ACTION_BOUNDS: dict[str, tuple[float, float]] = {
    "accept_job_offer": (0, 1),
    "take_major_loan": (1_000, 20_000),
    "move_house": (0, 1),
    "pursue_education": (0, 1),
    "decline": (0, 1),
}
MIN_RATIONALE_LENGTH = 10


@dataclass
class ValidationResult:
    approved: bool
    reason: str


def validate_policy_proposal(proposal: dict[str, Any]) -> ValidationResult:
    action = proposal.get("action")
    value = proposal.get("value")
    rationale = proposal.get("rationale", "")

    if action not in ALLOWED_POLICY_ACTIONS:
        return ValidationResult(False, f"'{action}' is not an allowed policy action")

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return ValidationResult(False, "value must be numeric")

    low, high = ALLOWED_POLICY_ACTIONS[action]
    if not low <= value <= high:
        return ValidationResult(False, f"value {value} is outside the allowed range [{low}, {high}] for {action}")

    if not isinstance(rationale, str) or len(rationale) < MIN_RATIONALE_LENGTH:
        return ValidationResult(False, "rationale is required and must be a substantive explanation")

    return ValidationResult(True, "proposal is within policy bounds")


def _validate_bounded_proposal(
    proposal: dict[str, Any],
    bounds: dict[str, tuple[float, float]],
    label: str,
) -> ValidationResult:
    action = proposal.get("action")
    value = proposal.get("amount")
    rationale = proposal.get("rationale", "")

    if action not in bounds:
        return ValidationResult(False, f"'{action}' is not an allowed {label} action")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return ValidationResult(False, "amount must be numeric")

    low, high = bounds[action]
    if not low <= value <= high:
        return ValidationResult(False, f"amount {value} is outside the allowed range [{low}, {high}] for {action}")

    if not isinstance(rationale, str) or len(rationale) < MIN_RATIONALE_LENGTH:
        return ValidationResult(False, "rationale is required and must be a substantive explanation")

    return ValidationResult(True, f"proposal is within {label} bounds")


def validate_business_proposal(business: Any, proposal: dict[str, Any]) -> ValidationResult:
    result = _validate_bounded_proposal(proposal, BUSINESS_ACTION_BOUNDS, "business")
    if not result.approved:
        return result
    if proposal.get("action") == "fire" and proposal.get("amount", 0) > business.headcount():
        return ValidationResult(False, "cannot fire more employees than the business currently has")
    return result


def validate_household_decision(proposal: dict[str, Any]) -> ValidationResult:
    return _validate_bounded_proposal(proposal, HOUSEHOLD_ACTION_BOUNDS, "household")
