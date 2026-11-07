# HECE/tests/unit/test_simulation.py
from hece.simulation import SimulationEngine
from hece.core.models.base import Hypothesis

LONG = "word " * 60  # passes the 50-word Substance Lock

def _hyp(**kw):
    base = dict(id="h", goal_id="g", description=LONG, feasibility_score=0.9)
    base.update(kw)
    return Hypothesis(**base)

def test_substance_lock_rejects_short():
    assert SimulationEngine().calculate_viability(_hyp(description="too short")) == 0.0

def test_verified_violation_zeroes_score():
    assert SimulationEngine().calculate_viability(_hyp(violated_hard_constraints=["x"])) == 0.0

def test_penalties_applied():
    h = _hyp(assumptions=["a"], logical_flaws=["f"])
    assert SimulationEngine().calculate_viability(h) == 0.7  # 0.9 - 0.15 - 0.05

def test_unverified_accusation_does_not_change_the_score():
    # The model's unproven opinion is shown (and sends the hypothesis to human review) but is not scored
    h = _hyp(unverified_violations=["Pauli exclusion principle"])
    assert SimulationEngine().calculate_viability(h) == 0.9

def test_rejection_reasons():
    e = SimulationEngine()
    assert "Substance Lock" in e.rejection_reason(_hyp(description="short"))
    r = e.rejection_reason(_hyp(violated_hard_constraints=["Law X"], violation_evidence=["Law X | quote: \"abc def ghi jkl\" | mechanism: m"]))
    assert "Verified violation" in r and "abc def ghi jkl" in r
    reason = e.rejection_reason(_hyp(feasibility_score=0.3, assumptions=["a", "b"]))
    assert "below the 65% threshold" in reason and "assumptions: 2" in reason

def test_evaluate_records_ai_estimate():
    h = _hyp(feasibility_score=0.9, assumptions=["a"])
    out = SimulationEngine().evaluate([h], None)[0]
    assert out.ai_estimate == 0.9 and out.feasibility_score == 0.85

def test_reason_mentions_unverified_accusations():
    r = SimulationEngine().rejection_reason(_hyp(feasibility_score=0.0, unverified_violations=["a", "b"]))
    assert "2 Critic accusation(s) could not be verified" in r

def test_red_flags_penalized_and_forces_review():
    desc = LONG + "the entropy of the system remains constant"
    out = SimulationEngine().evaluate([_hyp(description=desc)], None)[0]
    assert len(out.red_flags) == 1
    assert out.feasibility_score == 0.75 and out.status == "active"   # 0.9 - 0.15
    assert out.needs_human_review is True

def test_accepted_hypothesis_always_needs_review():
    out = SimulationEngine().evaluate([_hyp()], None)[0]
    assert out.status == "active" and out.needs_human_review is True

def test_borderline_rejection_is_flagged_for_review():
    e = SimulationEngine()
    out = e.evaluate([_hyp(feasibility_score=0.60)], None)[0]
    assert out.status == "rejected" and out.needs_human_review is True
    assert "Borderline" in e.rejection_reason(out)
    far = e.evaluate([_hyp(feasibility_score=0.30)], None)[0]
    assert far.needs_human_review is False and "Borderline" not in e.rejection_reason(far)


def test_speculative_engine_enforces_falsifiability_and_charges_for_postulates():
    spec = SimulationEngine(speculative=True)
    assert spec.calculate_viability(_hyp()) == 0.0                       # no prediction / refutation
    assert "Falsifiability Lock" in spec.rejection_reason(_hyp())
    ok = _hyp(prediction="a measurable 3 W output", refutation="no output at all", postulates=["q [kg]: x"])
    assert spec.calculate_viability(ok) == 0.8                           # 0.9 - 0.10 per postulate
    assert "postulates: 1" in spec.rejection_reason(_hyp(prediction="p", refutation="r", postulates=["q"], feasibility_score=0.1))
    assert SimulationEngine().calculate_viability(_hyp(postulates=["q"])) == 0.9   # classic mode ignores both

def test_speculative_mode_does_not_penalise_exotic_matter():
    desc = LONG + "the mechanism relies on exotic matter with negative energy density"
    assert len(SimulationEngine().evaluate([_hyp(description=desc)], None)[0].red_flags) == 1
    spec = SimulationEngine(speculative=True).evaluate([_hyp(description=desc, prediction="p", refutation="r")], None)[0]
    assert spec.red_flags == []


def test_numeric_inconsistency_costs_points_and_forces_review():
    wrong = SimulationEngine().evaluate([_hyp(description=LONG + "a speed of 300 m/s, which is 0.01c, is reached")], None)[0]
    assert len(wrong.numeric_flags) == 1 and wrong.feasibility_score == 0.75 and wrong.needs_human_review
    right = SimulationEngine().evaluate([_hyp(description=LONG + "a speed of 3e6 m/s, which is 0.01c, is reached")], None)[0]
    assert right.numeric_flags == []
    assert "numeric errors: 1" in SimulationEngine().rejection_reason(_hyp(feasibility_score=0.1, numeric_flags=["x"]))


def test_scale_mismatch_counts_as_a_verified_numeric_error():
    desc = LONG + "A resonator 10 \u00b5m wide.\nPrediction: a signal measured over a 1 cm^3 volume.\nRefutation: no signal at all."
    out = SimulationEngine().evaluate([_hyp(description=desc)], None)[0]
    assert len(out.numeric_flags) == 1 and "scale mismatch" in out.numeric_flags[0]
    assert out.feasibility_score == 0.75 and out.needs_human_review
