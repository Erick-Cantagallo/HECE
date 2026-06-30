# HECE/tests/unit/test_constraints.py
import pytest
from hece.core.models.base import Goal, GoalAnalysis, KnowledgeContext
from hece.constraints import ConstraintEngine

@pytest.fixture
def engine():
    return ConstraintEngine()

def test_process_constraints(engine):
    # Mocking inputs for testing
    goal = Goal(id="test-goal", description="test", domain="physics", complexity_level=10)
    analysis = GoalAnalysis(goal=goal, keywords=["test"], extracted_constraints=[])
    knowledge = KnowledgeContext(
        goal_id="test-goal",
        domain_laws=["Law of Testing"],
        known_facts=[],
        current_limitations=["Limit 1"]
    )
    
    boundaries = engine.process_constraints(analysis, knowledge)
    
    # Assertions to ensure boundaries are correctly mapped
    assert len(boundaries.hard_constraints) > 0
    assert "MUST NOT VIOLATE: Law of Testing" in boundaries.hard_constraints
    assert any("Limit 1" in crit for crit in boundaries.evaluation_criteria)