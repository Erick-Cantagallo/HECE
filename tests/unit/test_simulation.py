# HECE/tests/unit/test_simulation.py
import pytest
from hece.core.models.base import Hypothesis, ConstraintContext, Evidence
from hece.simulation import SimulationEngine

@pytest.fixture
def engine():
    return SimulationEngine()

def test_evaluate_hypothesis(engine):
    # Mocking a speculative hypothesis with supporting evidence
    hyp = Hypothesis(
        id="test-hyp",
        goal_id="test-goal",
        description="Testing simulation",
        supporting_evidence=[Evidence(id="ev1", description="Valid proof", reliability=0.8)],
        required_conditions=["Requires compute"],
        feasibility_score=0.5
    )
    constraints = ConstraintContext(goal_id="test-goal")
    
    evaluated = engine.evaluate([hyp], constraints)
    
    assert len(evaluated) == 1
    # Initial 0.5 + 0.15 (1 evidence bonus) = 0.65 -> active status
    assert evaluated[0].feasibility_score == 0.65
    assert evaluated[0].status == "active"