# HECE/tests/unit/test_pipeline.py
import json
import random
import re
from unittest.mock import patch

from hece.explorer import DiscoveryConfig
from hece.pipeline import run_discovery, offline_context
from hece.core.models.base import Goal, GoalAnalysis

GOAL = "reduce the energy consumption of seawater desalination"


def _pseudo(seed, n=60):
    rng = random.Random(seed * 7919 + 13)
    return " ".join("".join(rng.choice("bcdfghjklmnpqrstvwxz") + rng.choice("aeiou") for _ in range(3)) for _ in range(n))


def _cand(q, family, seed):
    return (f"TITLE: {family.title()} (q={q})\nFAMILY: {family}\nMECHANISM: {_pseudo(seed)}\n"
            "PREDICTION: Water flux of 12 litres per square metre per hour at a 20 K gradient and 1 bar of pressure.\n"
            "REFUTATION: A flux below 1 litre per square metre per hour at the same gradient would refute the idea.\n")


class _LLM:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def __call__(self, prompt, temperature=None):
        if "INTERNAL logical problems" in prompt:
            return "NO FLAWS"
        if "CHECKLIST OF LAWS" in prompt:
            return "NO LAWS BROKEN"
        if "Return ONLY a valid JSON object" in prompt:
            m = re.search(r"\(q=([0-9.]+)\)", prompt)
            return json.dumps({"assumptions": [], "required_conditions": [], "violated_hard_constraints": [],
                               "citations": [], "ai_viability_score": float(m.group(1)) if m else 0.5})
        return self.outputs.pop(0) if self.outputs else "garbage"


def test_end_to_end_without_network_and_without_pdf(tmp_path):
    llm = _LLM([_cand(0.3, "alpha pumping", 1), _cand(0.9, "gamma resonance", 2)])
    with patch("hece.agents.InferenceEngine.ask", new=llm):
        run = run_discovery("Unit Test", GOAL, DiscoveryConfig(max_iterations=5, target_count=1, seed=3, use_requirements=False),
                            use_rag=False, on_event=None, make_pdf=False, runs_dir=str(tmp_path))
    assert len(run.result.attempts) == 2 and len(run.result.accepted) == 1
    assert run.result.finished_reason == "target reached"
    assert "Prediction:" in run.conclusion and "NOT validated" in run.conclusion
    saved = json.loads(open(run.json_path, encoding="utf-8").read())
    assert saved["attempts"][1]["outcome"] == "accepted" and run.pdf_path is None
    assert "NOT grounded" in run.context.known_facts[0]


@patch("hece.paper.FPDF.output")
def test_pdf_receives_the_exploration_map(mock_output, tmp_path):
    llm = _LLM([_cand(0.3, "alpha pumping", 1), _cand(0.2, "beta tunnelling", 2)])
    with patch("hece.agents.InferenceEngine.ask", new=llm):
        run = run_discovery("Unit Test PDF", GOAL, DiscoveryConfig(max_iterations=2, target_count=3, seed=3, use_requirements=False),
                            use_rag=False, on_event=None, make_pdf=True, runs_dir=str(tmp_path))
    assert run.pdf_path and run.pdf_path.endswith(".pdf") and mock_output.called
    assert len(run.result.exploration_log()) == 2     # nothing passed: near-misses are shown instead


def test_offline_context_uses_domain_laws():
    analysis = GoalAnalysis(goal=Goal(id="x", description="anything", domain="chemistry"))
    ctx = offline_context(analysis)
    assert any("Pauli" in law for law in ctx.domain_laws)
    general = offline_context(GoalAnalysis(goal=Goal(id="y", description="anything")))
    assert any("Second Law" in law for law in general.domain_laws)


def test_user_requirements_flow_through_the_pipeline(tmp_path):
    mine = ["Move a 1 cm object between two points 1 m apart in under 3.3 ns"]
    llm = _LLM([_cand(0.3, "alpha pumping", 1)])
    with patch("hece.agents.InferenceEngine.ask", new=llm):
        run = run_discovery("Unit Test Req", GOAL, DiscoveryConfig(max_iterations=1, seed=3, use_requirements=False),
                            use_rag=False, on_event=None, make_pdf=False, runs_dir=str(tmp_path), requirements=mine)
    assert run.result.requirements == mine and run.result.requirements_source == "user"
    saved = json.loads(open(run.json_path, encoding="utf-8").read())
    assert saved["requirements"] == mine and saved["requirements_source"] == "user"
    assert "Requirements supplied by the user" in run.conclusion
