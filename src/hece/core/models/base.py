# HECE/src/hece/core/models/base.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone


# ---------------------------
# GOAL (Objetivo)
# ---------------------------
class Goal(BaseModel):
    id: str
    description: str
    domain: Optional[str] = None  # ex: biology, physics, general
    complexity_level: int = Field(ge=1, le=10, default=5)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------
# CONSTRAINT (Restrições)
# ---------------------------
class Constraint(BaseModel):
    id: str
    description: str
    type: str  # physical, biological, computational, ethical
    strictness: int = Field(ge=1, le=10, default=5)


# ---------------------------
# EVIDENCE (Base científica)
# ---------------------------
class Evidence(BaseModel):
    id: str
    description: str
    source: Optional[str] = None  # paper, dataset, theory
    reliability: float = Field(ge=0.0, le=1.0, default=0.5)


# ---------------------------
# HYPOTHESIS (o núcleo do HECE)
# ---------------------------
class Hypothesis(BaseModel):
    id: str
    goal_id: str

    description: str

    assumptions: List[str] = []
    required_conditions: List[str] = []

    supporting_evidence: List[Evidence] = []
    conflicting_evidence: List[Evidence] = []

    feasibility_score: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)

    status: str = "active"  # active, rejected, speculative, accepted


# ---------------------------
# SCIENTIFIC REPORT (saída final)
# ---------------------------
class ScientificReport(BaseModel):
    goal: Goal

    constraints: List[Constraint]
    hypotheses: List[Hypothesis]

    summary: str

    conclusion: str

    confidence_global: float = Field(ge=0.0, le=1.0, default=0.5)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------
# GOAL ANALYSIS (Saída do Interpreter)
# ---------------------------
class GoalAnalysis(BaseModel):
    """
    Represents the output of the Goal Interpreter, containing the structured
    Goal and any extracted metadata (keywords, initial constraints).
    """
    goal: Goal
    keywords: List[str] = []
    extracted_constraints: List[Constraint] = []


# ---------------------------
# KNOWLEDGE CONTEXT (Knowledge Engine Output)
# ---------------------------
class KnowledgeContext(BaseModel):
    """
    Represents the established scientific ground truths, laws, and 
    current limitations related to the user's goal domain.
    """
    goal_id: str
    domain_laws: List[str] = []
    known_facts: List[str] = []
    current_limitations: List[str] = []


# ---------------------------
# CONSTRAINT CONTEXT (Constraint Engine Output)
# ---------------------------
class ConstraintContext(BaseModel):
    """
    Consolidates user-defined constraints and scientific laws into strict 
    boundaries for the Hypothesis Engine.
    """
    goal_id: str
    hard_constraints: List[str] = []      # Cannot be violated (e.g., Laws of Physics)
    soft_constraints: List[str] = []      # Preferred conditions (if feasible)
    evaluation_criteria: List[str] = []   # Metrics to evaluate the future hypothesis