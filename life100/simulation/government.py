"""Government entity. SRS §6.5.

A structured policy-lever object, distinct from the freeform
`engine.policies` dict the Government Agent's validator already writes to
(kept for backward compatibility with the existing economy/tests) — this
gives the SRS-named fields a first-class home and something the API/
dashboard can display directly. `engine.py`'s POLICY_CHANGED handler updates
both the dict and, when the policy name matches one of these fields, this
object too.
"""

from __future__ import annotations

from dataclasses import dataclass

# policy action name (as used by agents/validator.py) -> Government field name
POLICY_FIELD_MAP = {
    "food_subsidy": "food_subsidy",
    "tax_rate": "tax_rate",
    "interest_rate": "interest_rate",
    "healthcare_spending": "healthcare_spending",
}


@dataclass
class Government:
    tax_rate: float = 0.15
    interest_rate: float = 0.05
    food_subsidy: float = 0.0
    healthcare_spending: float = 0.0
    education_spending: float = 0.0
    infrastructure_spending: float = 0.0
    business_regulation: float = 0.3
    environmental_regulation: float = 0.3
