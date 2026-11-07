# HECE/tests/unit/test_run_hece.py
"""End-to-end wiring of run_hece() (classic mode) with the LLM, arXiv and the PDF writer mocked."""
import json
import pytest
from unittest.mock import patch

from hece.inference import InferenceError
from hece.main import run_hece

GOAL = "How does quantum gravity work without extra dimensions"

# Long enough to pass the SimulationEngine substance lock (at least 50 words).
EXPERT_TEXT = ("Graviton Lattice Coupling: spacetime is modelled as a discrete lattice whose spacing sets a minimum "
               "length, and gravity emerges from correlations between neighbouring lattice cells. Each cell carries "
               "a small number of internal states, and the attraction between masses appears as a statistical bias "
               "in how those states align across the lattice. At large distances the bias averages out into the smooth "
               "curvature described by general relativity, so the model needs no extra spatial dimensions at all.")

SYNTHESIZER_JSON = json.dumps({
    "assumptions": ["Spacetime is discrete at the Planck scale"],
    "required_conditions": ["Condition 1"],
    "violated_hard_constraints": [],
    "citations": [],
    "ai_viability_score": 0.9,
})


def fake_llm(self, prompt, temperature=None):
    if "Return ONLY a valid JSON object" in prompt:
        return SYNTHESIZER_JSON
    if "INTERNAL logical problems" in prompt:
        return "NO FLAWS"
    if "CHECKLIST OF LAWS" in prompt:
        return "NO LAWS BROKEN"
    return EXPERT_TEXT


@patch("hece.main.PaperGenerator.generate_pdf", return_value="reports/HECE_Smoke.pdf")
@patch("hece.knowledge.ScientificToolbox.search_arxiv", return_value="LITERATURE: mocked")
@patch("hece.agents.InferenceEngine.ask", autospec=True, side_effect=fake_llm)
def test_full_pipeline(_ask, search_arxiv, generate_pdf):
    run_hece("Smoke", GOAL, 2)

    search_arxiv.assert_called_once()
    generate_pdf.assert_called_once()
    project, analysis, _context, boundaries, hypotheses, conclusion = generate_pdf.call_args.args

    assert project == "Smoke"
    assert analysis.goal.domain == "physics"
    assert any("Thermodynamics" in rule for rule in boundaries.hard_constraints)
    # Monte Carlo loop: only candidates with no broken law and >= 65% viability are kept
    assert len(hypotheses) == 2
    assert all(h.status == "active" and h.feasibility_score >= 0.65 for h in hypotheses)
    # The conclusion is deterministic (no LLM call)
    assert conclusion.startswith("2 of 2 hypotheses passed the automated screening.")


@patch("hece.main.PaperGenerator.generate_pdf", return_value="reports/HECE_Smoke.pdf")
@patch("hece.knowledge.ScientificToolbox.search_arxiv", return_value="LITERATURE: mocked")
@patch("hece.agents.InferenceEngine.ask", autospec=True)
def test_report_shows_the_best_near_misses_when_nothing_passes(mock_ask, _search, generate_pdf):
    scores = iter([0.3, 0.5, 0.2, 0.4])  # one AI estimate per attempt, all below the 65% threshold

    def low_scores(self, prompt, temperature=None):
        if "Return ONLY a valid JSON object" in prompt:
            return json.dumps({"assumptions": [], "required_conditions": [], "violated_hard_constraints": [],
                               "citations": [], "ai_viability_score": next(scores)})
        return fake_llm(self, prompt, temperature)

    mock_ask.side_effect = low_scores
    run_hece("Smoke", GOAL, 1)  # 1 requested -> 4 attempts, all rejected

    hypotheses, conclusion = generate_pdf.call_args.args[4], generate_pdf.call_args.args[5]
    assert [h.feasibility_score for h in hypotheses] == [0.5, 0.4, 0.3]
    assert all(h.status == "rejected" for h in hypotheses)
    assert conclusion.startswith("0 of 3 hypotheses passed") and "[REJECTED]" in conclusion


@patch("hece.main.PaperGenerator.generate_pdf")
@patch("hece.knowledge.ScientificToolbox.search_arxiv", return_value="LITERATURE: mocked")
@patch("hece.agents.InferenceEngine.ask", side_effect=InferenceError("Could not reach Ollama."))
def test_pipeline_stops_when_the_llm_is_unavailable(_ask, _search, generate_pdf):
    with pytest.raises(InferenceError):
        run_hece("Smoke", GOAL, 1)

    generate_pdf.assert_not_called()
