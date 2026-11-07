# HECE/tests/unit/test_reroute.py
"""REROUTE: an idea stopped by a physical law is not discarded; the next attempt looks for an alternative path."""
from unittest.mock import patch

from hece.agents import AgentPool
from hece.candidate import parse_candidate, validate_candidate, compose_description
from hece.conclusion import build_discovery_conclusion
from hece.core.models.base import Hypothesis
from hece.explorer import Attempt, DiscoveryConfig, DiscoveryEngine

from test_explorer import QUOTE, ScriptedLLM, make_cand, pseudo, setup

# A heat engine above the Carnot limit: lawchecks.py turns it into a VERIFIED Second Law violation.
CARNOT_BREAKER = (f"TITLE: Hot Box Engine (q=0.9)\nFAMILY: hot box engine\nMECHANISM: {pseudo(11)} The engine runs between "
                  "400 K and 300 K with a thermal efficiency of 60 percent.\n"
                  # no other temperature here: lawchecks uses the widest span stated in the text
                  "PREDICTION: The shaft delivers 6 kW for every 10 kW of heat drawn from the 400 K source.\n"
                  "REFUTATION: A flux below 1 litre per square metre per hour at the same gradient would refute the idea.\n")
ROUTE = ("ROUTE: the earlier engine broke the Second Law, so this version keeps the Carnot limit and pays for the extra "
         "output with a hotter source at 900 K supplied by concentrated sunlight\n")
REQUIRES = "REQUIRES: a selective absorber that survives 900 K for 10 years | SPEC: emissivity below 0.1 at 900 K\n"


def rerouted(q=0.9, route=ROUTE, requires=REQUIRES, seed=12):
    text = make_cand(q, "hot box engine solar", seed)
    head, tail = text.split("PREDICTION:")
    return head + route + requires + "PREDICTION:" + tail


def blocked_attempt(i=0):
    h = Hypothesis(id=f"h{i}", goal_id="g1", description="x " * 60, feasibility_score=0.0, status="rejected",
                   violated_hard_constraints=["MUST NOT VIOLATE: Second Law of Thermodynamics (Entropy increases)"],
                   violation_evidence=["[checked by Python] claims 60% heat-to-work efficiency"])
    return Attempt(index=i, strategy="explore", outcome="rejected", family=f"family {i}", score=0.0, hypothesis=h)


# ---------------------------------------------------------------------------------------------- format
def test_route_and_requires_are_parsed_and_shown_to_the_critic():
    cand = parse_candidate(rerouted())
    assert cand.route.startswith("the earlier engine broke the Second Law")
    assert cand.requires == ["a selective absorber that survives 900 K for 10 years | SPEC: emissivity below 0.1 at 900 K"]
    text = compose_description(cand)
    assert "Alternative path (law kept): the earlier engine" in text
    assert "Requires (does not exist yet): a selective absorber" in text


def test_a_reroute_must_state_its_route():
    issues, _ = validate_candidate(parse_candidate(rerouted(route="")), allow_new_physics=True, strategy="reroute")
    assert any("ROUTE" in i for i in issues)


def test_a_missing_technology_needs_a_numeric_spec():
    vague = "REQUIRES: a much better absorber | SPEC: as good as possible\n"
    issues, _ = validate_candidate(parse_candidate(rerouted(requires=vague)), allow_new_physics=True, strategy="reroute")
    assert any("REQUIRES" in i and "number" in i for i in issues)


# ---------------------------------------------------------------------------------------------- scheduler
def test_an_idea_stopped_by_a_law_is_rerouted_not_discarded():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(), on_event=None)
    strategy, parent = engine.choose_strategy(1, [blocked_attempt(0)])
    assert strategy == "reroute" and parent.index == 0


def test_reroute_happens_once_per_idea_and_never_twice_in_a_row():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(), on_event=None)
    first, second = blocked_attempt(0), blocked_attempt(1)
    done = Attempt(index=2, strategy="reroute", outcome="rejected", family="x", parent_index=0, score=0.1)
    assert engine.choose_strategy(3, [first, second, done])[0] != "reroute"          # not twice in a row
    filler = Attempt(index=3, strategy="explore", outcome="rejected", family="y", score=0.1)
    strategy, parent = engine.choose_strategy(4, [first, second, done, filler])
    assert strategy == "reroute" and parent.index == 1                               # attempt 0 was already rerouted


def test_a_failed_reroute_is_not_rerouted_again():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(), on_event=None)
    again = blocked_attempt(1)
    again.strategy, again.parent_index = "reroute", 0
    filler = Attempt(index=2, strategy="explore", outcome="rejected", family="y", score=0.1)
    assert engine.choose_strategy(3, [blocked_attempt(0), again, filler])[0] != "reroute"


def test_reroute_can_be_switched_off():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(reroute=False), on_event=None)
    assert engine.choose_strategy(1, [blocked_attempt(0)])[0] != "reroute"


# ---------------------------------------------------------------------------------------------- full loop
def run_loop(outputs, **cfg):
    config = DiscoveryConfig(**{"max_iterations": 2, "target_count": 5, "seed": 1, "use_requirements": False,
                                "confirmations": 0, **cfg})
    llm = ScriptedLLM(outputs)
    engine = DiscoveryEngine(AgentPool(), config, on_event=lambda m: None)
    with patch("hece.agents.InferenceEngine.ask", new=llm):
        return engine.run(*setup()), llm


def test_the_alternative_path_is_explored_and_reported():
    result, llm = run_loop([CARNOT_BREAKER, rerouted()])

    first, second = result.attempts
    assert first.outcome == "rejected" and first.hypothesis.violated_hard_constraints   # stopped by the Carnot check
    assert second.strategy == "reroute" and second.parent_index == 0
    prompt = llm.expert_prompts[1]
    assert "STRATEGY: REROUTE" in prompt and "Carnot" in prompt and "EARLIER CANDIDATE" in prompt

    h = second.hypothesis
    assert h.route.startswith("the earlier engine") and h.missing_technology
    assert h.feasibility_score == 0.8                       # 0.9 - 0.10 for one technology that does not exist yet
    assert second.outcome == "accepted"

    conclusion = build_discovery_conclusion(result)
    assert "reroute 1/1" in conclusion
    assert "What would have to be invented first" in conclusion and "selective absorber" in conclusion


def test_a_suspected_law_conflict_is_rerouted_after_proven_ones():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(), on_event=None)
    suspected = Attempt(index=1, strategy="explore", outcome="rejected", family="s", score=0.0,
                        hypothesis=Hypothesis(id="s", goal_id="g1", description="x " * 60, feasibility_score=0.0,
                                              status="rejected", unverified_violations=["(law cited) energy is created"]))
    assert engine.choose_strategy(2, [blocked_attempt(0), suspected])[1].index == 0      # proven first
    strategy, parent = engine.choose_strategy(2, [suspected])
    assert strategy == "reroute" and parent.index == 1
    prompt = engine.build_prompt("reroute", setup()[0], [suspected], [], parent, setup()[2])
    assert "(suspected by the Critic, not proven) (law cited) energy is created" in prompt


def test_a_missing_technology_that_breaks_a_law_is_called_out():
    result, _ = run_loop([CARNOT_BREAKER, rerouted(requires="REQUIRES: a vacuum engine | SPEC: 5e-3 J net work output from vacuum fluctuations\n")])
    conclusion = build_discovery_conclusion(result)
    assert "net work output from vacuum fluctuations  [this would itself contradict a law: extracting vacuum" in conclusion


def test_suspected_conflicts_leave_room_for_the_other_strategies():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(), on_event=None)

    def suspected(i):
        return Attempt(index=i, strategy="explore", outcome="rejected", family=f"s{i}", score=0.0,
                       hypothesis=Hypothesis(id=f"s{i}", goal_id="g1", description="x " * 60, feasibility_score=0.0,
                                             status="rejected", unverified_violations=["(law cited) energy is created"]))
    history = [suspected(0), suspected(1)]
    assert engine.choose_strategy(2, history)[0] != "reroute"          # only every third slot for suspicions
