"""Citizen entity model. SRS §6.1.

Citizens are mutable (their state changes over the simulation), but every
change of consequence must arrive as an applied Event (CLAUDE.md ground rule
4) — nothing outside `simulation/engine.py` should mutate a Citizen directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

FIRST_NAMES = (
    "Raj", "Maya", "John", "David", "Sarah", "Anita", "Kiran", "Priya",
    "Amit", "Sunita", "Rohan", "Neha", "Vikram", "Pooja", "Arjun", "Divya",
    "Sanjay", "Kavita", "Manoj", "Rekha", "Deepak", "Meera", "Suresh", "Anjali",
    "Ravi", "Lakshmi", "Nikhil", "Shreya", "Ajay", "Preeti",
)
LAST_NAMES = (
    "Sharma", "Gurung", "Thapa", "Shrestha", "Rai", "Basnet", "Adhikari",
    "Karki", "Bhattarai", "Poudel", "Khadka", "Lama", "Tamang", "Magar",
)
OCCUPATIONS = (
    "engineer", "teacher", "shopkeeper", "farmer", "doctor", "nurse",
    "clerk", "driver", "factory_worker", "accountant", "police_officer",
    "cook", "electrician", "student", "unemployed",
)


@dataclass
class Personality:
    risk_tolerance: float
    ambition: float
    patience: float
    social_tendency: float


@dataclass
class Citizen:
    citizen_id: str
    name: str
    age: int
    gender: str
    personality: Personality

    # Household / relationships
    household_id: str | None = None

    # Education
    education_level: str = "none"

    # Employment
    occupation: str = "unemployed"
    employer_id: str | None = None
    salary: float = 0.0
    employment_history: list[str] = field(default_factory=list)
    job_satisfaction: float = 0.5

    # Financial
    savings: float = 0.0
    debt: float = 0.0

    # Health
    health_score: float = 0.8
    stress: float = 0.2

    alive: bool = True

    def is_working_age(self) -> bool:
        return 18 <= self.age <= 65

    def is_child(self) -> bool:
        return self.age < 18
