# HECE/tests/unit/test_conclusion.py
from unittest.mock import MagicMock
from hece.conclusion import build_conclusion
from hece.core.models.base import Hypothesis

LONG = "word " * 60

def _h(status, **kw):
    base = dict(id="h", goal_id="g", description=LONG, feasibility_score=0.8, status=status)
    base.update(kw)
    return Hypothesis(**base)

def test_all_rejected_lists_reasons_without_llm():
    pool = MagicMock()
    text = build_conclusion(pool, [_h("rejected", description="too short", feasibility_score=0.0)])
    assert "0 of 1" in text and "Substance Lock" in text
    assert not pool.method_calls

def test_empty_list():
    assert "No valid hypotheses" in build_conclusion(MagicMock(), [])

def test_active_is_labelled_as_screening_not_validation_and_no_llm():
    pool = MagicMock()
    text = build_conclusion(pool, [_h("active", ai_estimate=0.9, red_flags=["x: 'y'"]), _h("rejected", feasibility_score=0.1)])
    assert "NOT validation" in text and "[ACTIVE]" in text and "Red flag: x: 'y'" in text and "[REJECTED]" in text
    assert not pool.method_calls


def test_discovery_conclusion_reports_counts_strategies_and_barriers():
    from hece.conclusion import build_discovery_conclusion
    from hece.explorer import Attempt, DiscoveryConfig, DiscoveryResult
    acc = _h("active", ai_estimate=0.9, title="Strain wave membrane", family="strain wave", strategy="recombine",
             prediction="Flux of 12 L per square metre per hour", refutation="A flux below 1 L would refute it",
             postulates=["torsion charge [kg m^2 s^-1]: x"])
    rej = _h("rejected", feasibility_score=0.2, red_flags=["entropy claimed constant: 'x'"])
    result = DiscoveryResult(goal="g", config=DiscoveryConfig(), finished_reason="target reached", attempts=[
        Attempt(index=0, strategy="explore", outcome="rejected", family="a", score=0.2, hypothesis=rej),
        Attempt(index=1, strategy="recombine", outcome="accepted", family="b", score=0.8, hypothesis=acc),
        Attempt(index=2, strategy="explore", outcome="duplicate", family="c")])
    text = build_discovery_conclusion(result)
    assert "3 attempt(s): 1 accepted, 1 rejected, 1 discarded as duplicates" in text
    assert "recombine 1/1" in text and "explore 0/2" in text
    assert "NOT validated" in text and "Postulated: torsion charge" in text and "Refutation:" in text
    assert "deterministic red flags (1)" in text

def test_discovery_conclusion_when_nothing_passes():
    from hece.conclusion import build_discovery_conclusion
    from hece.explorer import Attempt, DiscoveryConfig, DiscoveryResult
    rej = _h("rejected", feasibility_score=0.3, title="Idea")
    result = DiscoveryResult(goal="g", config=DiscoveryConfig(), finished_reason="iterations exhausted",
                             attempts=[Attempt(index=0, strategy="explore", outcome="rejected", hypothesis=rej, score=0.3)])
    text = build_discovery_conclusion(result)
    assert "valid result" in text and "Closest attempt 1" in text


def test_discovery_conclusion_reports_requirement_coverage_and_time():
    from hece.conclusion import build_discovery_conclusion
    from hece.explorer import Attempt, DiscoveryConfig, DiscoveryResult
    acc = _h("active", ai_estimate=0.9, title="T", family="f", strategy="explore", prediction="p 1", refutation="r 1",
             target="Sustain negative energy density")
    result = DiscoveryResult(goal="g", config=DiscoveryConfig(), finished_reason="all requirements covered",
                             requirements=["Sustain negative energy density in a cubic centimetre volume for a while", "Keep the throat open"],
                             attempts=[Attempt(index=0, strategy="explore", outcome="accepted", family="f", score=0.8,
                                               target=0, seconds=120.0, hypothesis=acc)])
    text = build_discovery_conclusion(result)
    assert "Average time per attempt: 2.0 min" in text
    assert "R1:" in text and "1 accepted, best 80%" in text and "R2:" in text and "0 accepted, best n/a" in text
    assert "does not achieve the goal" in text and "for: Sustain negative energy density" in text
