# HECE/tests/unit/test_hypothesis.py
import pytest
from unittest.mock import patch

from hece.hypothesis import HypothesisEngine
from hece.inference import InferenceError
from hece.core.models.base import Goal, GoalAnalysis, KnowledgeContext, ConstraintContext

VALID_LLM_JSON = (
    '{"description": "Mocked hypothesis", "assumptions": ["a", "b"], '
    '"required_conditions": ["c"], "feasibility_score": 0.5}'
)


@pytest.fixture
def inputs():
    goal = Goal(id="test", description="Test hypothesis", domain="physics", complexity_level=5)
    analysis = GoalAnalysis(goal=goal, keywords=["test"], extracted_constraints=[])
    knowledge = KnowledgeContext(goal_id="test", domain_laws=[], known_facts=[], current_limitations=[])
    constraints = ConstraintContext(goal_id="test", hard_constraints=[], soft_constraints=[], evaluation_criteria=[])
    return analysis, knowledge, constraints


# The LLM is always mocked: a unit test must not need Ollama (or a lucky model) to pass.
@patch("hece.hypothesis.InferenceEngine.ask", return_value=VALID_LLM_JSON)
def test_generate_hypotheses(_ask, inputs):
    hypotheses = HypothesisEngine().generate_hypotheses(*inputs)

    # Assertions to guarantee structural integrity (Legacy Engine)
    assert len(hypotheses) == 1
    assert hypotheses[0].status == "speculative"
    assert hypotheses[0].goal_id == "test"
    assert hypotheses[0].description == "Mocked hypothesis"
    assert hypotheses[0].assumptions == ["a", "b"]


@patch("hece.hypothesis.InferenceEngine.ask", return_value="```json\n" + VALID_LLM_JSON + "\n```")
def test_generate_hypotheses_strips_markdown_fences(_ask, inputs):
    assert len(HypothesisEngine().generate_hypotheses(*inputs)) == 1


@patch("hece.hypothesis.InferenceEngine.ask", return_value="Sorry, I can only chat.")
def test_generate_hypotheses_returns_nothing_for_non_json(_ask, inputs):
    assert HypothesisEngine().generate_hypotheses(*inputs) == []


@patch("hece.hypothesis.InferenceEngine.ask", side_effect=InferenceError("Could not reach Ollama."))
def test_generate_hypotheses_returns_nothing_when_the_llm_is_down(_ask, inputs):
    assert HypothesisEngine().generate_hypotheses(*inputs) == []
