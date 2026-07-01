# HECE/tests/unit/test_simulation.py
from hece.simulation import SimulationEngine
from hece.core.models.base import Hypothesis, ConstraintContext

def test_evaluate_hypothesis():
    engine = SimulationEngine()
    
    # Mocking a hypothesis with specific flaws to test the deterministic math penalties
    hyp = Hypothesis(
        id="test-hyp",
        goal_id="test-goal",
        description="Testing simulation math",
        assumptions=["Unproven assumption 1"],               # Penalty: -0.05
        violated_hard_constraints=["Broke thermodynamics"],  # Penalty: -0.40
        logical_flaws=[],                                    # Penalty: -0.00
        required_conditions=[],
        citations=[],
        feasibility_score=0.0
    )
    constraints = ConstraintContext(goal_id="test-goal")
    
    evaluated = engine.evaluate([hyp], constraints)
    
    assert len(evaluated) == 1
    
    # Math check: Base 1.0 - 0.40 (1 hard constraint) - 0.05 (1 assumption) = 0.55
    assert evaluated[0].feasibility_score == 0.55
    assert evaluated[0].status == "speculative"