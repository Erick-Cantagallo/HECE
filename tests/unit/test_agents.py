# HECE/tests/unit/test_agents.py
import pytest
from unittest.mock import patch
from hece.agents import AgentPool, InvestigationOrchestrator, _ensure_list, _max_retries
from hece.inference import InferenceError
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

VALID_SYNTHESIZER_JSON = '{"description": "Valid JSON output", "assumptions": ["Assumption 1"], "required_conditions": [], "violated_hard_constraints": [], "logical_flaws": [], "citations": []}'

def test_ensure_list_blocks_the_none_trap():
    assert _ensure_list(["None", "n/a", " Nothing ", "A real flaw"]) == ["A real flaw"]
    assert _ensure_list("None.") == []
    assert _ensure_list("a single string") == ["a single string"]
    assert _ensure_list(None) == []
    assert _ensure_list(42) == []

def test_max_retries_comes_from_the_environment(monkeypatch):
    assert _max_retries() == 3  # default, as documented in .env.example

    monkeypatch.setenv("MAX_RETRIES", "5")
    assert _max_retries() == 5

    monkeypatch.setenv("MAX_RETRIES", "not-a-number")
    assert _max_retries() == 3

    monkeypatch.setenv("MAX_RETRIES", "0")
    assert _max_retries() == 1  # at least one attempt, always

@patch('hece.agents.InferenceEngine.ask')
def test_orchestrator_honours_max_retries(mock_ask, mock_data, monkeypatch):
    monkeypatch.setenv("MAX_RETRIES", "1")
    mock_ask.side_effect = ["Expert Hypothesis Mock", "Critic Review Mock", "Invalid JSON attempt 1"]

    hypotheses = InvestigationOrchestrator(AgentPool()).investigate(*mock_data, target_count=1)

    assert hypotheses == []
    assert mock_ask.call_count == 3  # Expert + Critic + a single Synthesizer attempt

@patch('hece.agents.InferenceEngine.ask')
def test_orchestrator_recovers_when_a_retry_fixes_the_json(mock_ask, mock_data):
    mock_ask.side_effect = ["Expert Hypothesis Mock", "Critic Review Mock", "no json here", VALID_SYNTHESIZER_JSON]

    hypotheses = InvestigationOrchestrator(AgentPool()).investigate(*mock_data, target_count=1)

    assert len(hypotheses) == 1
    # The retry prompt tells the LLM what went wrong
    assert "CRITICAL ERROR PREVIOUSLY" in mock_ask.call_args_list[3].args[0]

@patch('hece.agents.InferenceEngine.ask')
def test_orchestrator_ignores_none_answers_from_the_llm(mock_ask, mock_data):
    mock_ask.side_effect = [
        "Expert Hypothesis Mock",
        "Critic Review Mock",
        '{"description": "D", "assumptions": "n/a", "required_conditions": ["None"], "violated_hard_constraints": ["None."], "logical_flaws": [], "citations": ["arXiv:1234"]}',
    ]

    hypothesis = InvestigationOrchestrator(AgentPool()).investigate(*mock_data, target_count=1)[0]

    assert hypothesis.assumptions == []
    assert hypothesis.required_conditions == []
    assert hypothesis.violated_hard_constraints == []
    assert hypothesis.citations == ["arXiv:1234"]

@patch('hece.agents.InferenceEngine.ask', side_effect=InferenceError("Could not reach Ollama."))
def test_orchestrator_does_not_swallow_an_llm_outage(_ask, mock_data):
    with pytest.raises(InferenceError):
        InvestigationOrchestrator(AgentPool()).investigate(*mock_data, target_count=1)