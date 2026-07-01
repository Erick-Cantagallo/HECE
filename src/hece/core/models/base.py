# HECE/src/hece/core/models/base.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone

# ---------------------------
# GOAL
# ---------------------------
class Goal(BaseModel):
    id: str
    description: str
    domain: Optional[str] = None  # e.g., biology, physics, general
    complexity_level: int = Field(ge=1, le=10, default=5)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ---------------------------
# CONSTRAINT
# ---------------------------
class Constraint(BaseModel):
    id: str
    description: str
    type: str  # physical, biological, computational, ethical
    strictness: int = Field(ge=1, le=10, default=5)

# ---------------------------
# EVIDENCE
# ---------------------------
class Evidence(BaseModel):
    id: str
    description: str
    source: Optional[str] = None  # paper, dataset, theory
    reliability: float = Field(ge=0.0, le=1.0, default=0.5)

# ---------------------------
# HYPOTHESIS (Core of HECE)
# ---------------------------
class Hypothesis(BaseModel):
    id: str
    goal_id: str

    description: str

    assumptions: List[str] = []
    required_conditions: List[str] = []
    citations: List[str] = []
    
    # NEW FIELDS FOR DETERMINISTIC CALCULATION
    violated_hard_constraints: List[str] = []
    logical_flaws: List[str] = []

    supporting_evidence: List[Evidence] = []
    conflicting_evidence: List[Evidence] = []

    feasibility_score: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)

    status: str = "active"  # active, rejected, speculative, accepted

# ---------------------------
# SCIENTIFIC REPORT (Final output)
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
# GOAL ANALYSIS (Interpreter Output)
# ---------------------------
class GoalAnalysis(BaseModel):
    goal: Goal
    keywords: List[str] = []
    extracted_constraints: List[Constraint] = []

# ---------------------------
# KNOWLEDGE CONTEXT (Knowledge Engine Output)
# ---------------------------
class KnowledgeContext(BaseModel):
    goal_id: str
    domain_laws: List[str] = []
    known_facts: List[str] = []
    current_limitations: List[str] = []

# ---------------------------
# CONSTRAINT CONTEXT (Constraint Engine Output)
# ---------------------------
class ConstraintContext(BaseModel):
    goal_id: str
    hard_constraints: List[str] = []      
    soft_constraints: List[str] = []      
    evaluation_criteria: List[str] = []