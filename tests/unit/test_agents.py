# HECE/tests/unit/test_agents.py
import pytest
from unittest.mock import patch
from hece.agents import AgentPool, InvestigationOrchestrator
from hece.core.models.base import GoalAnalysis, KnowledgeContext, ConstraintContext, Goal

@pytest.fixture
def mock_data():
    """Provides standard mock inputs for the Orchestrator."""
    goal = Goal(id="test-123", description="Test goal")
    analysis = GoalAnalysis(goal=goal)
    context = KnowledgeContext(goal_id="test-123")
    boundaries = ConstraintContext(goal_id="test-123")
    return analysis, context, boundaries

@patch('hece.agents.InferenceEngine.ask')
def test_orchestrator_successful_parsing(mock_ask, mock_data):
    analysis, context, boundaries = mock_data
    
    # Simulate LLM outputs: 1st (Expert), 2nd (Critic), 3rd (Synthesizer valid JSON)
    # Updated JSON mock to reflect the new deterministic schema (no feasibility_score)
    mock_ask.side_effect = [
        "Expert Hypothesis Mock",
        "Critic Review Mock",
        '{"description": "Valid JSON output", "assumptions": ["Assumption 1"], "required_conditions": [], "violated_hard_constraints": [], "logical_flaws": [], "citations": []}'
    ]
    
    pool = AgentPool()
    orchestrator = InvestigationOrchestrator(pool)
    hypotheses = orchestrator.investigate(analysis, context, boundaries, target_count=1)
    
    # Assertions
    assert len(hypotheses) == 1
    assert hypotheses[0].description == "Valid JSON output"
    assert len(hypotheses[0].assumptions) == 1
    # Feasibility is hardcoded to 0.0 by the orchestrator until the SimulationEngine processes it
    assert hypotheses[0].feasibility_score == 0.0

@patch('hece.agents.InferenceEngine.ask')
def test_orchestrator_auto_retry_failure(mock_ask, mock_data):
    analysis, context, boundaries = mock_data
    
    # Simulate LLM outputs: Expert, Critic, and then 3 failed Synthesizer attempts
    mock_ask.side_effect = [
        "Expert Hypothesis Mock",
        "Critic Review Mock",
        "Invalid JSON attempt 1",
        "Invalid JSON attempt 2",
        "Invalid JSON attempt 3"
    ]
    
    pool = AgentPool()
    orchestrator = InvestigationOrchestrator(pool)
    hypotheses = orchestrator.investigate(analysis, context, boundaries, target_count=1)
    
    # Assertions: It should gracefully fail and return 0 hypotheses, without crashing Python
    assert len(hypotheses) == 0