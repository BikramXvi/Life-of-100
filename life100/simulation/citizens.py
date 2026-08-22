"""Citizen entity model. SRS §6.1 — full field set (identity, education,
employment, financial, health, psychological, behavioral, goals, family
ties, relationships).

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

CAREER_GOALS = ("get promoted", "start a business", "change careers", "become a specialist", "retire early")
FINANCIAL_GOALS = ("buy a home", "pay off debt", "build savings", "invest in the market", "support family")
FAMILY_GOALS = ("get married", "raise children well", "reunite with family", "start a family", "care for parents")
PERSONAL_GOALS = ("travel", "learn a new skill", "improve health", "build community ties", "find stability")


@dataclass
class Personality:
    risk_tolerance: float
    ambition: float
    patience: float
    social_tendency: float


@dataclass
class Goals:
    """SRS §6.1 "Goals" — simple aspirational tags rather than a full
    planning system; used to bias decision-engine choices (simulation/
    decisions.py) and given to the Household Decision Agent as context."""

    career_goal: str
    financial_goal: str
    family_goal: str
    personal_goal: str


@dataclass
class Citizen:
    citizen_id: str
    name: str
    age: int
    gender: str
    personality: Personality

    # Household / relationships
    household_id: str | None = None

    # Family ties (SRS §6.3)
    spouse_id: str | None = None
    parent_ids: list[str] = field(default_factory=list)
    children_ids: list[str] = field(default_factory=list)
    marital_status: str = "single"  # single | married | divorced | widowed

    # Education
    education_level: str = "none"
    skills: list[str] = field(default_factory=list)
    academic_performance: float = 0.5

    # Employment
    occupation: str = "unemployed"
    employer_id: str | None = None
    salary: float = 0.0
    employment_history: list[str] = field(default_factory=list)
    experience_years: float = 0.0
    job_satisfaction: float = 0.5

    # Financial
    savings: float = 0.0
    debt: float = 0.0
    assets: float = 0.0
    credit_score: float = 650.0
    investments: float = 0.0

    # Health
    health_score: float = 0.8
    fitness: float = 0.7
    stress: float = 0.2
    sleep: float = 0.7
    medical_history: list[str] = field(default_factory=list)
    healthcare_visits: int = 0

    # Behavioral (SRS §6.1 "Behavioral")
    spending_habit: float = 0.5  # 0 = frugal, 1 = spendthrift
    leisure_activity: str = "recreation"

    # Goals
    goals: Goals | None = None

    alive: bool = True

    def is_working_age(self) -> bool:
        return 18 <= self.age <= 65

    def is_child(self) -> bool:
        return self.age < 18

    def is_married(self) -> bool:
        return self.marital_status == "married" and self.spouse_id is not None
