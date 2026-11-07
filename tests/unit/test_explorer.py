# HECE/tests/unit/test_explorer.py
import json
import random
import re
from unittest.mock import patch

from hece.agents import AgentPool
from hece.core.models.base import ConstraintContext, Goal, GoalAnalysis, Hypothesis, KnowledgeContext
from hece.explorer import (Attempt, DiscoveryConfig, DiscoveryEngine, consecutive_failures, jaccard, keyword_set)
from hece.inference import InferenceError

LAWS = ["MUST NOT VIOLATE: First Law of Thermodynamics (Energy cannot be created or destroyed)"]
QUOTE = "Water flux of 12 litres"


def pseudo(seed, n=60):
    """Unique pseudo-words so that distinct candidates are never 'too similar'."""
    rng = random.Random(seed * 7919 + 13)
    return " ".join("".join(rng.choice("bcdfghjklmnpqrstvwxz") + rng.choice("aeiou") for _ in range(3)) for _ in range(n))


def make_cand(q, family, seed, postulate=False, flaw=False, lawflaw=False, confirmfail=False):
    marks = (" FLAWMARK" if flaw else "") + (" LAWFLAW" if lawflaw else "") + (" CONFIRMFAIL" if confirmfail else "")
    text = f"TITLE: {family.title()} (q={q}){marks}\nFAMILY: {family}\nMECHANISM: {pseudo(seed)}\n"
    if postulate:
        text += ("NEW QUANTITY: lattice torsion charge | SYMBOL: Qt | DIMENSIONS: kg m^3 s^-1 | DEFINITION: a conserved count of "
                 "lattice twist per unit length | EQUATION: dQt/dt = k * E * B | MAGNITUDE: < 1e-12 m^3 s^-2 | COUPLING: it "
                 "couples to phonon momentum through a dimensionless constant | REDUCES TO KNOWN PHYSICS WHEN: the coupling "
                 "constant tends to zero\n")
    text += (f"PREDICTION: {QUOTE} per square metre per hour at a 20 K gradient and 1 bar of pressure.\n"
             "REFUTATION: A flux below 1 litre per square metre per hour at the same gradient would refute the idea.\n")
    return text


class ScriptedLLM:
    """Deterministic stand-in for the local model. Each Expert call pops the next scripted answer."""
    def __init__(self, expert_outputs, requirements=None, taint=False):
        self.expert_outputs = list(expert_outputs)
        self.requirements = requirements
        self.taint = taint
        self.expert_prompts = []
        self.requirement_prompts = []
        self.flaw_prompts = []
        self.temperatures = {"expert": [], "judge": []}
        self.synth_calls = 0

    def __call__(self, prompt, temperature=None):
        if "EFFECTS that must be ACHIEVED" in prompt:
            self.requirement_prompts.append(prompt)
            if isinstance(self.requirements, list):
                return self.requirements.pop(0) if self.requirements else "I cannot think of any."
            return self.requirements or "I cannot think of any."
        if "INTERNAL logical problems" in prompt:
            self.flaw_prompts.append(prompt)
            self.temperatures["judge"].append(temperature)
            if "CONFIRMFAIL" in prompt and temperature == 0.5:      # only the confirmation round sees the problems
                return (f"FLAW: The flux claim is asserted without any mechanism that explains it | QUOTE: {QUOTE}\n"
                        f"FLAW: The mechanism step is stated without a physical justification here | QUOTE: {QUOTE}")
            if "LAWFLAW" in prompt:
                return f"FLAW: The prediction contradicts the second law of thermodynamics here | QUOTE: {QUOTE}"
            if "FLAWMARK" in prompt:
                return f"FLAW: The predicted flux is asserted without a mechanism that explains it | QUOTE: {QUOTE}"
            return "NO FLAWS"
        if "CHECKLIST OF LAWS" in prompt:
            self.temperatures["judge"].append(temperature)
            return "NO LAWS BROKEN"
        if "Return ONLY a valid JSON object" in prompt:
            self.synth_calls += 1
            self.temperatures["judge"].append(temperature)
            m = re.search(r"\(q=([0-9.]+)\)", prompt)
            q = float(m.group(1)) if m else 0.5
            if self.taint and "discarded" not in prompt:      # a Critic that accuses every law without proof
                bogus = [{"law": f"Invented law {k}", "quote": "nothing like this in the text", "mechanism": "x"} for k in range(3)]
                return json.dumps({"assumptions": [], "required_conditions": [], "violated_hard_constraints": bogus,
                                   "citations": [], "ai_viability_score": 0.0})
            return json.dumps({"assumptions": [], "required_conditions": [], "violated_hard_constraints": [],
                               "citations": [], "ai_viability_score": q})
        if "OUTPUT FORMAT" in prompt:
            self.temperatures["expert"].append(temperature)
            self.expert_prompts.append(prompt)
            return self.expert_outputs.pop(0) if self.expert_outputs else "garbage"
        return "NO FLAWS"


def setup():
    analysis = GoalAnalysis(goal=Goal(id="g1", description="reduce the energy consumption of seawater desalination", domain="physics"))
    context = KnowledgeContext(goal_id="g1", domain_laws=["Conservation of energy"], known_facts=["NO RELEVANT LITERATURE WAS RETRIEVED"])
    boundaries = ConstraintContext(goal_id="g1", hard_constraints=list(LAWS))
    return analysis, context, boundaries


def run_engine(outputs, requirements=None, taint=False, force=None, user_reqs=None, **cfg):
    stop = cfg.pop("_stop", None)
    config = DiscoveryConfig(**{"max_iterations": 6, "target_count": 5, "seed": 1,
                                "use_requirements": requirements is not None, **cfg})
    llm = ScriptedLLM(outputs, requirements, taint)
    engine = DiscoveryEngine(AgentPool(), config, on_event=lambda m: None, should_stop=stop)
    if force:
        engine.choose_strategy = lambda i, attempts: (force, None)
    with patch("hece.agents.InferenceEngine.ask", new=llm):
        result = engine.run(*setup(), requirements=user_reqs)
    return result, llm, engine


def dummy_attempt(i, outcome="rejected", score=0.5, strategy="explore", family=None):
    h = Hypothesis(id=f"h{i}", goal_id="g1", description="x " * 60, feasibility_score=score, status=outcome)
    return Attempt(index=i, strategy=strategy, outcome=outcome, family=family or f"family {i}", score=score, hypothesis=h)


# ---------------------------------------------------------------------------------------------- helpers
def test_similarity_helpers():
    assert jaccard(keyword_set("graphene membrane strain wave"), keyword_set("graphene membrane strain wave")) == 1.0
    assert jaccard(keyword_set("graphene membrane"), keyword_set("plasma torch")) == 0.0


def test_consecutive_failures_resets_on_accept():
    seq = [dummy_attempt(0), dummy_attempt(1, "accepted", 0.9), dummy_attempt(2), dummy_attempt(3)]
    assert consecutive_failures(seq) == 2


# ---------------------------------------------------------------------------------------------- scheduler
def test_scheduler_follows_the_documented_rules():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(), on_event=None)
    assert engine.choose_strategy(0, [])[0] == "explore"
    assert engine.choose_strategy(1, [dummy_attempt(0, score=0.2)])[0] == "recombine"
    assert engine.choose_strategy(2, [dummy_attempt(0, score=0.2), dummy_attempt(1, score=0.2)])[0] == "explore"
    near = [dummy_attempt(0, score=0.2), dummy_attempt(1, score=0.5)]
    strategy, parent = engine.choose_strategy(2, near)
    assert strategy == "refine" and parent.index == 1
    three_failures = [dummy_attempt(i, score=0.1) for i in range(3)]
    assert engine.choose_strategy(3, three_failures)[0] == "postulate"


def test_new_physics_can_be_switched_off():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(allow_new_physics=False), on_event=None)
    assert engine.choose_strategy(3, [dummy_attempt(i, score=0.1) for i in range(3)])[0] == "recombine"


def test_a_parent_is_refined_at_most_twice():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(max_refinements_per_parent=1), on_event=None)
    seq = [dummy_attempt(0, score=0.5), dummy_attempt(1, score=0.1, strategy="refine")]
    seq[1].parent_index = 0
    assert engine.best_near_miss(seq) is None


# ---------------------------------------------------------------------------------------------- full loop
def test_loop_stops_when_target_is_reached_and_refines_the_near_miss():
    outputs = [make_cand(0.3, "alpha pumping", 1), make_cand(0.4, "beta tunnelling", 2), make_cand(0.9, "gamma resonance", 3)]
    result, llm, _ = run_engine(outputs, target_count=1, max_iterations=10)
    assert [a.outcome for a in result.attempts] == ["rejected", "rejected", "accepted"]
    assert [a.strategy for a in result.attempts] == ["explore", "recombine", "refine"]
    assert result.attempts[2].parent_index == 1
    assert result.finished_reason == "target reached"
    best = result.accepted[0]
    assert best.status == "active" and best.needs_human_review and best.feasibility_score == 0.9
    assert best.parent_id == result.attempts[1].hypothesis.id and best.iteration == 3


def test_duplicate_family_is_discarded_before_any_assessment():
    outputs = [make_cand(0.3, "alpha pumping", 1), make_cand(0.3, "Alpha Pumping!", 2), make_cand(0.3, "delta fusion", 3)]
    result, llm, _ = run_engine(outputs, max_iterations=3)
    assert [a.outcome for a in result.attempts] == ["rejected", "duplicate", "rejected"]
    assert "same mechanism family" in result.attempts[1].reason
    assert llm.synth_calls == 2          # the duplicate cost no assessment calls


def test_too_similar_mechanism_is_discarded():
    same_words = make_cand(0.3, "alpha pumping", 1)
    twin = same_words.replace("FAMILY: alpha pumping", "FAMILY: totally different name")
    result, _, _ = run_engine([same_words, twin], max_iterations=2)
    assert result.attempts[1].outcome == "duplicate" and "too similar" in result.attempts[1].reason


def test_format_failure_is_retried_once_with_feedback():
    result, llm, _ = run_engine(["garbage", make_cand(0.3, "alpha pumping", 1)], max_iterations=1)
    assert result.attempts[0].outcome == "rejected"
    assert "previous answer was rejected" in llm.expert_prompts[1]
    result, _, _ = run_engine(["garbage", "still garbage"], max_iterations=1)
    assert result.attempts[0].outcome == "invalid" and result.attempts[0].reason.startswith("invalid format")


def test_candidate_without_prediction_never_reaches_the_critic():
    no_prediction = make_cand(0.9, "alpha pumping", 1).split("PREDICTION:")[0]
    result, llm, _ = run_engine([no_prediction, no_prediction], max_iterations=1)
    assert result.attempts[0].outcome == "invalid" and llm.synth_calls == 0


def test_new_physics_gating_and_postulate_cost():
    with_q = make_cand(0.85, "torsion lattice", 1, postulate=True)
    result, llm, _ = run_engine([with_q], force="postulate", max_iterations=1, target_count=1)
    hyp = result.accepted[0]
    assert len(hyp.postulates) == 1 and hyp.feasibility_score == 0.75     # 0.85 - 0.10 (a new law has a price)
    assert "NEW QUANTITY:" in llm.expert_prompts[0] and "required: exactly 1" in llm.expert_prompts[0]

    # the same candidate is invalid when the strategy is not POSTULATE, or when new physics is switched off
    result, llm, _ = run_engine([with_q] * 3, force="explore", max_iterations=1)
    assert result.attempts[0].outcome == "invalid" and "only allowed in POSTULATE" in result.attempts[0].reason
    assert "Do NOT postulate" in llm.expert_prompts[0]
    result, _, _ = run_engine([with_q] * 3, force="postulate", allow_new_physics=False, max_iterations=1)
    assert result.attempts[0].outcome == "invalid"


def test_postulate_strategy_appears_after_repeated_failures():
    outputs = [make_cand(0.2, f"family number {n} idea", n) for n in range(1, 4)] + \
              [make_cand(0.2, "family number 4 idea", 4, postulate=True)]
    result, llm, _ = run_engine(outputs, max_iterations=4)
    assert [a.strategy for a in result.attempts] == ["explore", "recombine", "explore", "postulate"]
    assert "STRATEGY: POSTULATE" in llm.expert_prompts[3] and "barriers" in llm.expert_prompts[3]
    assert all("Do NOT postulate" in p for p in llm.expert_prompts[:3])
    assert result.attempts[3].hypothesis.postulates
    result, _, _ = run_engine([make_cand(0.2, f"family number {n} idea", n) for n in range(1, 8)],
                              max_iterations=4, allow_new_physics=False)
    assert "postulate" not in [a.strategy for a in result.attempts]


def test_recombine_uses_reproducible_seed_concepts():
    outputs = [make_cand(0.2, "alpha pumping", 1), make_cand(0.2, "beta tunnelling", 2)]
    r1, llm, _ = run_engine(outputs, max_iterations=2, seed=5)
    concepts = r1.attempts[1].concepts
    assert len(concepts) == 3 and all(c in llm.expert_prompts[1] for c in concepts)
    r2, _, _ = run_engine([make_cand(0.2, "alpha pumping", 1), make_cand(0.2, "beta tunnelling", 2)], max_iterations=2, seed=5)
    assert r2.attempts[1].concepts == concepts


def test_refine_prompt_lists_the_problems_of_the_parent():
    outputs = [make_cand(0.2, "alpha pumping", 1), make_cand(0.75, "beta tunnelling", 2, flaw=True), make_cand(0.2, "gamma idea", 3)]
    result, llm, _ = run_engine(outputs, max_iterations=3)
    assert result.attempts[1].hypothesis.logical_flaws          # the grounded flaw was counted
    assert result.attempts[1].outcome == "rejected"             # 0.75 - 0.15 = 0.60 < 0.65
    assert result.attempts[2].strategy == "refine"
    assert "asserted without a mechanism" in llm.expert_prompts[2]


def test_stop_callback_and_state_persistence(tmp_path):
    calls = {"n": 0}
    def stop():
        calls["n"] += 1
        return calls["n"] > 1
    result, _, _ = run_engine([make_cand(0.3, "alpha pumping", 1)], _stop=stop)
    assert result.finished_reason == "stopped by user" and len(result.attempts) == 1

    path = result.save(str(tmp_path / "runs" / "run.json"))
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["goal"].startswith("reduce the energy") and data["finished_reason"] == "stopped by user"
    row = data["attempts"][0]
    assert row["strategy"] == "explore" and row["hypothesis"]["prediction"].startswith("Water flux")


def test_llm_outage_mid_run_keeps_the_attempts_made_so_far(tmp_path):
    class DyingLLM(ScriptedLLM):
        def __call__(self, prompt, temperature=None):
            if "OUTPUT FORMAT" in prompt and not self.expert_outputs:
                raise InferenceError("Could not reach Ollama.")
            return super().__call__(prompt, temperature)

    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(max_iterations=6, target_count=5, seed=1, use_requirements=False),
                             on_event=lambda m: None)
    path = tmp_path / "run.json"
    with patch("hece.agents.InferenceEngine.ask", new=DyingLLM([make_cand(0.3, "alpha pumping", 1)])):
        result = engine.run(*setup(), save_path=str(path))

    assert len(result.attempts) == 1
    assert result.finished_reason.startswith("local LLM unavailable") and "Could not reach Ollama." in result.finished_reason
    assert json.loads(path.read_text(encoding="utf-8"))["finished_reason"] == result.finished_reason


def test_boundaries_add_universal_laws_and_biology_only_when_relevant():
    engine = DiscoveryEngine(AgentPool(), DiscoveryConfig(), on_event=None)
    analysis, _, base = setup()
    plain = engine.boundaries_for(base, ["resonance"], analysis).hard_constraints
    assert any("Second Law" in c for c in plain) and not any("Central dogma" in c for c in plain)
    bio = engine.boundaries_for(base, ["spider silk"], analysis).hard_constraints
    assert any("Central dogma" in c for c in bio)


# ---------------------------------------------------------------------------------------------- findings from real runs
def test_refining_the_same_idea_twice_is_not_a_duplicate():
    """Real run: siblings of one refinement chain were discarded as 'same family'."""
    outputs = [make_cand(0.5, "alpha pumping", 1), make_cand(0.1, "beta tunnelling", 2),
               make_cand(0.5, "alpha pumping", 3), make_cand(0.1, "delta fusion", 4),
               make_cand(0.1, "epsilon waves", 5), make_cand(0.5, "alpha pumping", 6)]
    result, _, _ = run_engine(outputs, max_iterations=6, allow_new_physics=False)
    assert [a.strategy for a in result.attempts][2] == "refine" and result.attempts[2].parent_index == 0
    assert result.attempts[5].strategy == "refine" and result.attempts[5].outcome == "rejected"   # not 'duplicate'


def test_an_unchanged_refinement_is_still_a_duplicate():
    same = make_cand(0.5, "alpha pumping", 1)
    result, _, _ = run_engine([same, make_cand(0.1, "beta tunnelling", 2), same], max_iterations=3)
    assert result.attempts[2].strategy == "refine" and result.attempts[2].outcome == "duplicate"
    assert "unchanged" in result.attempts[2].reason


def test_judges_run_cold_and_the_inventor_runs_hot():
    result, llm, _ = run_engine([make_cand(0.3, "alpha pumping", 1)], max_iterations=1)
    assert set(llm.temperatures["judge"]) == {0.1} and set(llm.temperatures["expert"]) == {0.9}


def test_a_critic_that_accuses_every_law_does_not_set_the_score():
    result, llm, _ = run_engine([make_cand(0.8, "alpha pumping", 1)], taint=True, max_iterations=1)
    hyp = result.attempts[0].hypothesis
    assert hyp.ai_estimate == 0.8                           # recomputed from the hypothesis, not from the accusations
    assert len(hyp.unverified_violations) == 3 and hyp.needs_human_review
    assert any("recomputed" in n for n in hyp.speculative_notes)
    assert llm.synth_calls == 2


def test_flaws_that_cite_a_law_become_accusations_not_flaws():
    result, _, _ = run_engine([make_cand(0.8, "alpha pumping", 1, lawflaw=True)], max_iterations=1)
    hyp = result.attempts[0].hypothesis
    assert hyp.logical_flaws == []
    assert len(hyp.unverified_violations) == 1 and "law cited in the flaw review" in hyp.unverified_violations[0]
    assert hyp.needs_human_review and hyp.feasibility_score == 0.7    # 0.8 - 0.10 (accusation, not 0.15 flaw)


REQS = ("REQUIREMENT: Sustain a negative energy density of at least 1e-6 J per cubic metre in a one cubic centimetre volume\n"
        "REQUIREMENT: Keep the throat of the structure open for at least 1 ms against gravitational collapse\n")


def test_requirements_are_derived_and_attempts_rotate_over_them():
    outputs = [make_cand(0.2, "alpha pumping", 1), make_cand(0.2, "beta tunnelling", 2)]
    result, llm, _ = run_engine(outputs, requirements=REQS, max_iterations=2)
    assert len(result.requirements) == 2
    assert [a.target for a in result.attempts] == [0, 1]
    assert "TARGET REQUIREMENT" in llm.expert_prompts[0] and "negative energy density" in llm.expert_prompts[0]
    assert "throat" in llm.expert_prompts[1]
    assert result.attempts[1].hypothesis.target.startswith("Keep the throat")
    rows = result.requirement_coverage()
    assert [r["attempts"] for r in rows] == [1, 1] and rows[0]["accepted"] == 0


def test_a_refinement_keeps_the_target_of_its_parent():
    outputs = [make_cand(0.5, "alpha pumping", 1), make_cand(0.1, "beta tunnelling", 2), make_cand(0.5, "alpha pumping", 3)]
    result, _, _ = run_engine(outputs, requirements=REQS, max_iterations=3, allow_new_physics=False)
    assert result.attempts[2].strategy == "refine" and result.attempts[2].target == result.attempts[0].target == 0


def test_the_run_ends_when_every_requirement_has_a_candidate():
    outputs = [make_cand(0.9, "alpha pumping", 1), make_cand(0.9, "beta tunnelling", 2), make_cand(0.9, "gamma idea", 3)]
    result, _, _ = run_engine(outputs, requirements=REQS, max_iterations=6)
    assert len(result.attempts) == 2 and result.finished_reason == "all requirements covered"
    assert [a.target for a in result.attempts] == [0, 1] and all(a.outcome == "accepted" for a in result.attempts)


def test_unusable_requirements_fall_back_to_the_plain_goal():
    result, llm, _ = run_engine([make_cand(0.2, "alpha pumping", 1)], requirements="Nothing useful here.", max_iterations=1)
    assert result.requirements == [] and result.attempts[0].target is None
    assert len(llm.requirement_prompts) == 2           # one retry
    assert "TARGET REQUIREMENT" not in llm.expert_prompts[0]


def test_attempts_are_timed_and_logged():
    result, _, _ = run_engine([make_cand(0.3, "alpha pumping", 1)], max_iterations=1)
    assert result.attempts[0].seconds >= 0 and "seconds" in result.exploration_log()[0]



# ---------------------------------------------------------------------------------------------- findings from the third run
BAD_REQS = ("REQUIREMENT: The energy density of the portal must be greater than or equal to the energy density of the surrounding space\n"
            "REQUIREMENT: The speed of the particles traversing the portal must be less than or equal to the speed of light in a vacuum\n"
            "REQUIREMENT: The stress and strain on the portal material must be within the material's elastic limit of the structure\n")


def test_vacuous_requirements_are_rejected_and_the_model_is_told_why():
    result, llm, _ = run_engine([make_cand(0.2, "alpha pumping", 1)], requirements=[BAD_REQS, REQS], max_iterations=1)
    assert len(result.requirements) == 2 and result.requirements[0].startswith("Sustain a negative")
    assert len(llm.requirement_prompts) == 2
    assert "was rejected" in llm.requirement_prompts[1] and "no numeric target" in llm.requirement_prompts[1]
    assert "do NOT list laws" in llm.requirement_prompts[0]


def test_user_supplied_requirements_replace_the_derived_ones():
    mine = ["Move a 1 cm object between two points 1 m apart in under 3.3 ns", "Keep the link open for at least 1 s"]
    result, llm, _ = run_engine([make_cand(0.2, "alpha pumping", 1)], requirements=REQS, user_reqs=mine, max_iterations=1)
    assert result.requirements == mine and result.requirements_source == "user"
    assert llm.requirement_prompts == []                      # the model was not asked
    assert "Move a 1 cm object" in llm.expert_prompts[0]


def test_a_refinement_chain_is_cut_after_the_root_cap():
    outputs = [make_cand(0.5, "alpha pumping", 1), make_cand(0.1, "beta tunnelling", 2), make_cand(0.5, "alpha pumping", 3),
               make_cand(0.1, "delta fusion", 4), make_cand(0.1, "epsilon waves", 5), make_cand(0.1, "zeta lattice", 6)]
    result, _, _ = run_engine(outputs, max_iterations=6, allow_new_physics=False, max_refinements_per_root=1)
    assert result.attempts[2].strategy == "refine"
    assert "refine" not in [a.strategy for a in result.attempts[3:]]       # the chain already used its one refinement


def test_arithmetic_errors_in_a_candidate_cost_points_and_force_review():
    wrong = make_cand(0.8, "alpha pumping", 1).replace("PREDICTION: ", "PREDICTION: A speed of 300 m/s, which is 0.01c, is measured; ")
    result, _, _ = run_engine([wrong], max_iterations=1)
    hyp = result.attempts[0].hypothesis
    assert len(hyp.numeric_flags) == 1 and hyp.feasibility_score == 0.65 + 0.0 or hyp.feasibility_score == 0.65
    assert hyp.needs_human_review


def test_the_flaw_critic_is_told_to_look_for_circularity_and_unbuildable_setups():
    result, llm, _ = run_engine([make_cand(0.3, "alpha pumping", 1)], requirements=REQS, max_iterations=1)
    prompt = llm.flaw_prompts[0]
    assert "circular" in prompt and "could not be built in a laboratory" in prompt and "TARGET REQUIREMENT" in prompt



# ---------------------------------------------------------------------------------------------- findings from the fifth run
def test_a_would_be_active_candidate_must_survive_independent_confirmation():
    """Real run: the ACTIVE was a lucky judgement (exactly 65%) that a second look would not have repeated."""
    result, llm, _ = run_engine([make_cand(0.8, "alpha pumping", 1, confirmfail=True)], max_iterations=1, target_count=1)
    a = result.attempts[0]
    assert a.outcome == "rejected" and result.accepted == []
    assert a.hypothesis.confirmation_scores == [0.8, 0.5, 0.5] and a.score == 0.5
    assert "Failed confirmation" in a.reason and "80%, 50%, 50%" in a.reason
    assert any(n.startswith("confirmation round") for n in a.hypothesis.speculative_notes)
    assert a.hypothesis.needs_human_review


def test_a_candidate_that_repeats_its_score_is_accepted_and_confirmation_runs_hotter():
    result, llm, _ = run_engine([make_cand(0.9, "alpha pumping", 1)], max_iterations=1, target_count=1)
    hyp = result.accepted[0]
    assert hyp.confirmation_scores == [0.9, 0.9, 0.9]
    assert 0.5 in llm.temperatures["judge"] and 0.1 in llm.temperatures["judge"]
    assert llm.synth_calls == 3                       # 1 assessment + 2 confirmations


def test_confirmation_can_be_switched_off():
    result, llm, _ = run_engine([make_cand(0.9, "alpha pumping", 1)], max_iterations=1, target_count=1, confirmations=0)
    assert result.accepted[0].confirmation_scores == [] and llm.synth_calls == 1


def test_rejected_candidates_cost_no_confirmation_calls():
    result, llm, _ = run_engine([make_cand(0.3, "alpha pumping", 1)], max_iterations=1)
    assert llm.synth_calls == 1


def test_a_refinement_must_be_rewritten_in_full_and_a_diff_is_invalid():
    outputs = [make_cand(0.5, "alpha pumping", 1), make_cand(0.1, "beta tunnelling", 2)]
    result, llm, _ = run_engine(outputs + [make_cand(0.5, "alpha pumping", 3)], max_iterations=3, allow_new_physics=False)
    assert "COMPLETE candidate" in llm.expert_prompts[2] and "never write 'as before'" in llm.expert_prompts[2]
    diff = make_cand(0.5, "alpha pumping", 3).replace("MECHANISM: ", "MECHANISM: The refined design maintains the core idea of the earlier candidate; ")
    result, _, _ = run_engine(outputs + [diff] * 3, max_iterations=3, allow_new_physics=False)
    assert result.attempts[2].strategy == "refine" and result.attempts[2].outcome == "invalid"
    assert "refers to an earlier version" in result.attempts[2].reason
