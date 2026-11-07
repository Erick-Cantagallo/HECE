# HECE/tests/unit/test_agents.py
import json
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
        "NO FLAWS",
        '{"description": "Valid JSON output", "assumptions": ["Assumption 1"], "required_conditions": [], "violated_hard_constraints": [], "logical_flaws": [], "citations": [], "ai_viability_score": 0.8}'
    ]
    
    pool = AgentPool()
    orchestrator = InvestigationOrchestrator(pool)
    hypotheses = orchestrator.investigate(analysis, context, boundaries, target_count=1)
    
    # Assertions
    assert len(hypotheses) == 1
    assert hypotheses[0].description == "Expert Hypothesis Mock"  # Expert text is kept as-is
    assert len(hypotheses[0].assumptions) == 1
    # The AI's own estimate is stored as-is until the SimulationEngine processes it
    assert hypotheses[0].feasibility_score == 0.8
    assert hypotheses[0].ai_estimate == 0.8

@patch('hece.agents.InferenceEngine.ask')
def test_orchestrator_auto_retry_failure(mock_ask, mock_data):
    analysis, context, boundaries = mock_data
    
    # Simulate LLM outputs: Expert, Critic, and then 3 failed Synthesizer attempts
    mock_ask.side_effect = [
        "Expert Hypothesis Mock",
        "Critic Review Mock",
        "NO FLAWS",
        "Invalid JSON attempt 1",
        "Invalid JSON attempt 2",
        "Invalid JSON attempt 3"
    ]
    
    pool = AgentPool()
    orchestrator = InvestigationOrchestrator(pool)
    hypotheses = orchestrator.investigate(analysis, context, boundaries, target_count=1)
    
    # Assertions: It should gracefully fail and return 0 hypotheses, without crashing Python
    assert len(hypotheses) == 0

@patch('hece.agents.InferenceEngine.ask')
def test_fake_accusation_is_flagged_not_zeroed(mock_ask, mock_data):
    analysis, context, _ = mock_data
    boundaries = ConstraintContext(goal_id="test-123", hard_constraints=["MUST NOT VIOLATE: Pauli exclusion principle"])
    synth = json.dumps({
        "description": "Water desalination using graphene membranes " * 10,
        "assumptions": [], "required_conditions": [], "logical_flaws": [], "citations": [],
        "violated_hard_constraints": [{"law": "Pauli exclusion principle", "quote": "this quote is not in the text", "mechanism": "short"}],
        "ai_viability_score": 0.8,
    })
    mock_ask.side_effect = ["Expert text about desalination", "Critic text", "NO FLAWS", synth]

    hyp = InvestigationOrchestrator(AgentPool()).investigate(analysis, context, boundaries, target_count=1)[0]

    assert hyp.violated_hard_constraints == []
    assert hyp.unverified_violations == ["Pauli exclusion principle"]
    assert hyp.needs_human_review is True

@patch('hece.agents.InferenceEngine.ask')
def test_proven_accusation_is_kept(mock_ask, mock_data):
    analysis, context, _ = mock_data
    boundaries = ConstraintContext(goal_id="test-123", hard_constraints=["MUST NOT VIOLATE: Conservation of mass and energy"])
    expert = "The device creates energy from nothing by looping its output back into its input."
    synth = json.dumps({
        "description": "A looped device.", "assumptions": [], "required_conditions": [],
        "logical_flaws": [], "citations": [],
        "violated_hard_constraints": [{
            "law": "Conservation of mass and energy", "quote": "creates energy from nothing",
            "mechanism": "The device outputs more energy than it receives, so energy is being created, which contradicts conservation of energy."}],
        "ai_viability_score": 0.9,
    })
    mock_ask.side_effect = [expert, "Critic text", "NO FLAWS", synth]

    hyp = InvestigationOrchestrator(AgentPool()).investigate(analysis, context, boundaries, target_count=1)[0]

    assert hyp.violated_hard_constraints == ["Conservation of mass and energy"]
    assert "creates energy from nothing" in hyp.violation_evidence[0]
    assert hyp.needs_human_review is True  # a veto must always be visible to a human
    assert hyp.unverified_violations == []


@patch('hece.agents.InferenceEngine.ask')
def test_invented_citations_are_dropped(mock_ask, mock_data):
    analysis, _, boundaries = mock_data
    context = KnowledgeContext(goal_id="test-123", known_facts=[
        "REAL SCIENTIFIC LITERATURE RETRIEVED:\n\n- Title: The Higgs Portal and Cosmology\n  ID: 1412.4743\n  Summary: x\n"])
    synth = json.dumps({"assumptions": [], "required_conditions": [], "logical_flaws": [], "violated_hard_constraints": [],
                        "citations": ["The Higgs Portal and Cosmology", "Invented paper (arXiv:2012.12345)"],
                        "ai_viability_score": 0.5})
    mock_ask.side_effect = ["Expert text", "NO LAWS BROKEN", "NO FLAWS", synth]

    hyp = InvestigationOrchestrator(AgentPool()).investigate(analysis, context, boundaries, target_count=1)[0]

    assert hyp.citations == ["The Higgs Portal and Cosmology (arXiv:1412.4743)"]


@patch('hece.agents.InferenceEngine.ask')
def test_missing_score_triggers_retry_not_silent_zero(mock_ask, mock_data):
    analysis, context, boundaries = mock_data
    no_score = '{"assumptions": [], "required_conditions": [], "violated_hard_constraints": [], "logical_flaws": [], "citations": []}'
    ok = '{"assumptions": [], "required_conditions": [], "violated_hard_constraints": [], "logical_flaws": [], "citations": [], "ai_viability_score": 0.4}'
    mock_ask.side_effect = ["Expert text", "NO LAWS BROKEN", "NO FLAWS", no_score, ok]

    hyps = InvestigationOrchestrator(AgentPool()).investigate(analysis, context, boundaries, target_count=1)

    assert len(hyps) == 1 and hyps[0].ai_estimate == 0.4


def test_null_like_items_are_not_counted_as_flaws():
    from hece.agents import _ensure_list
    items = ["No explicit contradictions found", "None identified", "No evidence is provided for the mechanism"]
    assert _ensure_list(items) == ["No evidence is provided for the mechanism"]


@patch('hece.agents.InferenceEngine.ask')
def test_only_grounded_flaws_are_counted(mock_ask, mock_data):
    analysis, context, boundaries = mock_data
    expert = "The device ensures that the entropy of the system remains constant while it works."
    review = ("FLAW: The text claims entropy stays constant while also claiming a net gain | QUOTE: entropy of the system remains constant\n"
              "FLAW: This problem was simply invented by the critic | QUOTE: words that never appear in the text")
    synth = json.dumps({"assumptions": [], "required_conditions": [], "violated_hard_constraints": [],
                        "citations": [], "ai_viability_score": 0.7})
    mock_ask.side_effect = [expert, "NO LAWS BROKEN", review, synth]

    hyp = InvestigationOrchestrator(AgentPool()).investigate(analysis, context, boundaries, target_count=1)[0]

    assert len(hyp.logical_flaws) == 1 and "entropy of the system remains constant" in hyp.logical_flaws[0]

def test_empty_string_items_are_not_counted():
    from hece.agents import _ensure_list
    assert _ensure_list(["", "  ", "...", "A real assumption"]) == ["A real assumption"]


@patch('hece.agents.InferenceEngine.ask')
def test_numbered_reference_in_text_becomes_citation(mock_ask, mock_data):
    _, _, boundaries = mock_data
    analysis = GoalAnalysis(goal=Goal(id="test-123", description="reduce the energy consumption of seawater desalination"))
    context = KnowledgeContext(goal_id="test-123", known_facts=[
        "REAL SCIENTIFIC LITERATURE RETRIEVED:\n\n- [1] Title: Nanoporous Carbon Nitride\n  ID: 1512.07101\n  Summary: x\n"])
    synth = json.dumps({"assumptions": ["Novel approach to reduce energy consumption in seawater desalination"], "required_conditions": [], "violated_hard_constraints": [],
                        "citations": [], "ai_viability_score": 0.7})
    mock_ask.side_effect = ["We build on the membrane reported in [1].", "NO LAWS BROKEN", "NO FLAWS", synth]

    hyp = InvestigationOrchestrator(AgentPool()).investigate(analysis, context, boundaries, target_count=1)[0]

    assert hyp.citations == ["Nanoporous Carbon Nitride (arXiv:1512.07101)"]
    assert hyp.assumptions == []   # it only restates the goal


VALID_SYNTHESIZER_JSON = '{"assumptions": ["Assumption 1"], "required_conditions": [], "violated_hard_constraints": [], "citations": [], "ai_viability_score": 0.7}'

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
    mock_ask.side_effect = ["Expert Hypothesis Mock", "Critic Review Mock", "NO FLAWS", "Invalid JSON attempt 1"]

    hypotheses = InvestigationOrchestrator(AgentPool()).investigate(*mock_data, target_count=1)

    assert hypotheses == []
    assert mock_ask.call_count == 4  # Expert + Critic (laws) + Critic (flaws) + a single Synthesizer attempt

@patch('hece.agents.InferenceEngine.ask')
def test_orchestrator_recovers_when_a_retry_fixes_the_json(mock_ask, mock_data):
    mock_ask.side_effect = ["Expert Hypothesis Mock", "Critic Review Mock", "NO FLAWS", "no json here", VALID_SYNTHESIZER_JSON]

    hypotheses = InvestigationOrchestrator(AgentPool()).investigate(*mock_data, target_count=1)

    assert len(hypotheses) == 1
    # The retry prompt tells the LLM what went wrong
    assert "ERROR: Fix JSON formatting" in mock_ask.call_args_list[4].args[0]

@patch('hece.agents.InferenceEngine.ask')
def test_orchestrator_ignores_none_answers_from_the_llm(mock_ask, mock_data):
    mock_ask.side_effect = [
        "Expert Hypothesis Mock",
        "Critic Review Mock",
        "NO FLAWS",
        '{"assumptions": "n/a", "required_conditions": ["None"], "violated_hard_constraints": [], "citations": [], "ai_viability_score": 0.6}',
    ]

    hypothesis = InvestigationOrchestrator(AgentPool()).investigate(*mock_data, target_count=1)[0]

    assert hypothesis.assumptions == []
    assert hypothesis.required_conditions == []
    assert hypothesis.violated_hard_constraints == []

@patch('hece.agents.InferenceEngine.ask', side_effect=InferenceError("Could not reach Ollama."))
def test_orchestrator_does_not_swallow_an_llm_outage(_ask, mock_data):
    with pytest.raises(InferenceError):
        InvestigationOrchestrator(AgentPool()).investigate(*mock_data, target_count=1)
