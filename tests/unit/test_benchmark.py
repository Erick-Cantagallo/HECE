# HECE/tests/unit/test_benchmark.py
import json
from unittest.mock import patch

import pytest

from hece.benchmark import CaseResult, load_cases, main, run_benchmark, summarize

NO_PROBLEMS = {"assumptions": [], "required_conditions": [], "violated_hard_constraints": [], "citations": []}


def scripted_llm(score_by_marker):
    """Critic finds nothing; the Synthesizer's AI estimate depends on a marker word in the hypothesis."""
    def ask(self, prompt, temperature=None):
        if "INTERNAL logical problems" in prompt:
            return "NO FLAWS"
        if "CHECKLIST OF LAWS" in prompt:
            return "NO LAWS BROKEN"
        score = next((v for k, v in score_by_marker.items() if k in prompt), 0.5)
        return json.dumps({**NO_PROBLEMS, "ai_viability_score": score})
    return ask


def test_shipped_cases_are_valid_and_balanced():
    cases = load_cases()
    assert len({c.id for c in cases}) == len(cases)
    assert {c.expected for c in cases} == {"pass", "fail"}
    # every text must clear the SimulationEngine substance lock (50 words), or the benchmark measures nothing
    assert all(len(c.hypothesis.split()) >= 50 for c in cases)


def test_load_cases_rejects_an_unknown_verdict(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"cases": [{"id": "x", "expected": "maybe", "goal": "g", "hypothesis": "h"}]}))
    with pytest.raises(ValueError, match="expected must be"):
        load_cases(str(path))


@patch("hece.agents.InferenceEngine.ask", autospec=True)
def test_the_perpetual_motion_case_is_caught_without_the_model(mock_ask):
    # Even if the model rates it 90%, the deterministic red-flag screen must keep it below the threshold
    mock_ask.side_effect = scripted_llm({"Self-running permanent magnet motor": 0.9})
    case = next(c for c in load_cases() if c.id == "bad-perpetual-magnet-motor")

    [result] = run_benchmark([case], on_event=lambda m: None)

    assert result.red_flags and result.status == "rejected" and result.correct


@patch("hece.agents.InferenceEngine.ask", autospec=True)
def test_a_good_case_with_a_high_estimate_and_no_problems_passes(mock_ask):
    mock_ask.side_effect = scripted_llm({"Air-source heat pump": 0.9})
    case = next(c for c in load_cases() if c.id == "good-heat-pump")

    [result] = run_benchmark([case], on_event=lambda m: None)

    assert result.status == "active" and result.score == 0.9 and result.correct


def test_summarize_reports_confusion_and_separation():
    results = [CaseResult("g1", "pass", 1, "active", score=0.8), CaseResult("g2", "pass", 1, "rejected", score=0.5),
               CaseResult("b1", "fail", 1, "rejected", score=0.3), CaseResult("b2", "fail", 1, "failed")]
    s = summarize(results)

    assert (s["good_passed"], s["good_total"], s["bad_passed"], s["bad_total"]) == (1, 2, 0, 1)
    assert s["failed"] == 1 and s["accuracy"] == pytest.approx(2 / 3, abs=1e-3)
    assert s["separation_margin"] == 0.2  # a threshold between 0.3 and 0.5 would separate them


@patch("hece.agents.InferenceEngine.ask", autospec=True)
def test_cli_writes_the_results_file(mock_ask, tmp_path, capsys):
    mock_ask.side_effect = scripted_llm({})
    out = tmp_path / "bench.json"

    assert main(["--only", "good-riblets", "--out", str(out)]) == 0

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["summary"]["runs"] == 1 and data["results"][0]["id"] == "good-riblets"
    assert "Good hypotheses accepted" in capsys.readouterr().out


def test_cli_rejects_an_unknown_case(capsys):
    assert main(["--only", "no-such-case"]) == 1
