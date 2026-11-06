# HECE/tests/unit/test_pipeline.py
"""End-to-end wiring of run_hece() with the LLM, arXiv and the PDF writer mocked."""
import json
import pytest
from unittest.mock import patch

from hece.inference import InferenceError
from hece.main import run_hece

GOAL = "How does quantum gravity work without extra dimensions"

SYNTHESIZER_JSON = json.dumps({
    "description": "A mocked but well-formed hypothesis.",
    "assumptions": ["Assumption 1"],
    "required_conditions": ["Condition 1"],
    "violated_hard_constraints": [],
    "logical_flaws": ["Flaw 1"],
    "citations": ["arXiv:0000.00000"],
})


def fake_llm(self, prompt):
    # Only the Synthesizer's JSON step contains this instruction; every other call is free text.
    if "strict data output API" in prompt:
        return SYNTHESIZER_JSON
    return "Plain-text answer from the local model."


@patch("hece.main.PaperGenerator.generate_pdf", return_value="reports/HECE_Smoke.pdf")
@patch("hece.knowledge.ScientificToolbox.search_arxiv", return_value="LITERATURE: mocked")
@patch("hece.agents.InferenceEngine.ask", autospec=True, side_effect=fake_llm)
def test_full_pipeline(_ask, search_arxiv, generate_pdf):
    run_hece("Smoke", GOAL, 2)

    search_arxiv.assert_called_once_with("quantum gravity extra")
    generate_pdf.assert_called_once()
    project, analysis, _context, boundaries, hypotheses, conclusion = generate_pdf.call_args.args

    assert project == "Smoke"
    assert analysis.goal.domain == "physics"
    assert any("Thermodynamics" in rule for rule in boundaries.hard_constraints)
    assert len(hypotheses) == 2
    # Deterministic score: 1.00 - 0.15 (one flaw) - 0.05 (one assumption) = 0.80 -> active
    assert all(h.feasibility_score == 0.80 and h.status == "active" for h in hypotheses)
    assert conclusion == "Plain-text answer from the local model."


@patch("hece.main.PaperGenerator.generate_pdf")
@patch("hece.knowledge.ScientificToolbox.search_arxiv", return_value="LITERATURE: mocked")
@patch("hece.agents.InferenceEngine.ask", side_effect=InferenceError("Could not reach Ollama."))
def test_pipeline_stops_when_the_llm_is_unavailable(_ask, _search, generate_pdf):
    with pytest.raises(InferenceError):
        run_hece("Smoke", GOAL, 1)

    generate_pdf.assert_not_called()
