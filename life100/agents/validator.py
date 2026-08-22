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
