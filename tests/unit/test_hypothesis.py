# HECE/tests/unit/test_hypothesis.py
from hece.hypothesis import HypothesisEngine
from hece.core.models.base import Goal, GoalAnalysis, KnowledgeContext, ConstraintContext

def test_generate_hypotheses():
    engine = HypothesisEngine()
    goal = Goal(id="test", description="Test hypothesis", domain="physics", complexity_level=5)
    analysis = GoalAnalysis(goal=goal, keywords=["test"], extracted_constraints=[])
    knowledge = KnowledgeContext(goal_id="test", domain_laws=[], known_facts=[], current_limitations=[])
    constraints = ConstraintContext(goal_id="test", hard_constraints=[], soft_constraints=[], evaluation_criteria=[])
    
    hypotheses = engine.generate_hypotheses(analysis, knowledge, constraints)
    
    # Assertions to guarantee structural integrity (Updated for V1.0)
    assert len(hypotheses) == 1
    assert hypotheses[0].status == "speculative"
    assert len(hypotheses[0].assumptions) > 0
    # The outdated supporting_evidence assertion was removed since we use 'citations' now.