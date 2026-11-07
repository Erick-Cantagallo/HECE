# HECE/tests/unit/test_knowledge.py
import pytest
from unittest.mock import patch

from hece.core.models.base import Goal, GoalAnalysis
from hece.knowledge import KnowledgeEngine


@pytest.fixture(autouse=True)
def arxiv_search():
    """RAG would query the real arXiv API (slow, rate-limited, needs internet): always mock it."""
    with patch("hece.knowledge.ScientificToolbox.search_arxiv", return_value="LITERATURE: mocked") as mocked:
        yield mocked


@pytest.fixture
def engine():
    return KnowledgeEngine()

@pytest.fixture
def physics_analysis():
    # Mocking a GoalAnalysis for testing
    goal = Goal(id="test-123", description="quantum gravity", domain="physics", complexity_level=8)
    return GoalAnalysis(goal=goal, keywords=["quantum", "gravity"], extracted_constraints=[])

def test_retrieve_physics_context(engine, physics_analysis):
    context = engine.retrieve_context(physics_analysis)
    
    assert context.goal_id == "test-123"
    # Ensure thermodynamics laws are injected for physics
    assert any("Thermodynamics" in law for law in context.domain_laws)
    # Ensure specific keyword triggers limitations
    assert any("quantum gravity" in lim for lim in context.current_limitations)
    # Ensure high complexity triggers the framework limitation
    assert any("exceeds standard" in lim for lim in context.current_limitations)

def test_retrieve_context_injects_arxiv_literature(engine, physics_analysis, arxiv_search):
    context = engine.retrieve_context(physics_analysis)

    # The query is built from the top keywords and the papers land in the known facts
    arxiv_search.assert_called_once_with("quantum gravity", keywords=["quantum", "gravity"], use_cache=True)
    assert "LITERATURE: mocked" in context.known_facts

def test_retrieve_fallback_context(engine):
    # Testing an unknown domain to ensure safe fallback
    goal = Goal(id="test-456", description="Unknown test", domain=None, complexity_level=2)
    analysis = GoalAnalysis(goal=goal, keywords=["test"])
    context = engine.retrieve_context(analysis)
    
    assert "General Scientific Method rules apply" in context.domain_laws
    assert len(context.current_limitations) == 0

def test_unknown_domain_gets_universal_physical_limits(engine):
    goal = Goal(id="test-789", description="portal gun", domain=None, complexity_level=2)
    context = engine.retrieve_context(GoalAnalysis(goal=goal, keywords=["portal", "gun"]))
    assert "General Scientific Method rules apply" in context.domain_laws
    assert any("Thermodynamics" in law for law in context.domain_laws)
