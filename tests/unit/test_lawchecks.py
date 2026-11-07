# HECE/tests/unit/test_lawchecks.py
from hece.core.models.base import ConstraintContext, Hypothesis
from hece.lawchecks import carnot_limit, find_carnot_violations
from hece.simulation import SimulationEngine

LAWS = ConstraintContext(goal_id="g", hard_constraints=["MUST NOT VIOLATE: Second Law of Thermodynamics (Entropy increases)"])
FILLER = " The design is described in detail with materials, dimensions and operating conditions." * 6


def test_carnot_limit():
    assert carnot_limit(400, 300) == 0.25


def test_efficiency_above_carnot_is_a_violation():
    [(law, evidence)] = find_carnot_violations(
        "Exhaust at 400 K, cooling water at 300 K. The cycle converts 60 percent of the recovered heat into electricity.")
    assert "Second Law" in law and "60%" in evidence and "25.0%" in evidence


def test_celsius_is_converted_and_a_legal_efficiency_passes():
    # Carnot between 550 C and 30 C is about 63%: a 40% steam cycle is fine
    assert find_carnot_violations("Steam at 550 C, condenser at 30 C, thermal efficiency of 40 percent.") == []


def test_no_check_without_two_temperatures_or_a_heat_to_work_claim():
    assert find_carnot_violations("The tandem solar cell reaches an efficiency of 33 percent.") == []
    assert find_carnot_violations("The pump runs at 300 K with 95 percent efficiency.") == []
    assert find_carnot_violations("A heat pump at 35 C and 0 C has a COP of 3.5.") == []


def test_simulation_turns_a_carnot_violation_into_a_verified_violation():
    text = ("Organic Rankine cycle between 400 K and 300 K with a thermal efficiency of 55 percent." + FILLER)
    hyp = Hypothesis(id="h", goal_id="g", description=text, feasibility_score=0.9)

    [result] = SimulationEngine().evaluate([hyp], LAWS)

    assert result.status == "rejected" and result.feasibility_score == 0.0
    assert result.violated_hard_constraints == LAWS.hard_constraints
    assert result.violation_evidence[0].startswith("[checked by Python]")
