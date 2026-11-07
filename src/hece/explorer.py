# HECE/src/hece/explorer.py
"""
Discovery engine ("inventor mode").

Instead of refining one idea, it EXPLORES: it keeps an archive of everything it tried (and why each
attempt failed) and chooses the next move deterministically:

  explore    -> a mechanism from a family that was NOT tried yet
  recombine  -> force a mechanism out of 2-3 unrelated seed concepts (materials, organisms, phenomena...)
  refine     -> fix the specific problems of a near-miss (x -> x1)
  postulate  -> when attempts keep hitting barriers, allow a NEW physical quantity/law (explicitly declared,
                with symbol, equation, magnitude, SI dimensions and a "reduces to known physics when" condition)

Before exploring, the goal is decomposed into measurable PHYSICAL REQUIREMENTS. Each attempt targets one of them,
so the prediction has to measure something that actually matters instead of inventing a whole device at once.

Every candidate goes through the same deterministic screen as classic mode (verified law violations,
grounded flaws, red flags, 65% threshold) plus the Falsifiability Lock. ACTIVE still means
"worth testing", never "proven".
"""
import json
import random
import re
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from hece.agents import AgentPool, InvestigationOrchestrator, build_book
from hece.inference import InferenceError
from hece.candidate import (Candidate, parse_candidate, split_requirements, validate_candidate,
                            compose_description, format_postulate)
from hece.concepts import sample_concepts, concept_category
from hece.core.models.base import ConstraintContext, GoalAnalysis, Hypothesis, KnowledgeContext
from hece.simulation import SimulationEngine

# Laws that must hold in inventor mode (empirical generalisations, not negotiable).
UNIVERSAL_LAWS: List[str] = [
    "First Law of Thermodynamics (Energy cannot be created or destroyed)",
    "Second Law of Thermodynamics (Entropy increases)",
    "Speed of light in a vacuum is an absolute limit (c)",
    "Conservation of mass and energy",
    "Conservation of electric charge and momentum",
    "Material stress and strain limits",
]
BIOLOGY_LAWS: List[str] = [
    "Central dogma of molecular biology (DNA -> RNA -> Protein)",
    "Living systems obey chemical thermodynamics",
]

_STOP = set("""this that with from which will would could their there these those through between using used into
over under than then also each such only most more other same very when where while within without about because
device system process method mechanism approach based step stage energy""".split())

STRATEGIES = ("explore", "recombine", "refine", "postulate")


@dataclass
class DiscoveryConfig:
    max_iterations: int = 12
    target_count: int = 2
    allow_new_physics: bool = True
    use_requirements: bool = True
    max_requirements: int = 4
    seed: Optional[int] = None
    recombine_seeds: int = 3
    max_refinements_per_parent: int = 2
    max_refinements_per_root: int = 2   # a chain x -> x1 -> x2 is cut after this many refinements
    near_miss_score: float = 0.40
    postulate_after_failures: int = 3
    novelty_threshold: float = 0.55
    expert_temperature: float = 0.9
    format_retries: int = 2
    confirmations: int = 2              # extra independent assessments a would-be ACTIVE candidate must survive
    confirmation_temperature: float = 0.5
    max_minutes: Optional[float] = None


@dataclass
class Attempt:
    index: int                      # 0-based iteration number
    strategy: str
    outcome: str                    # accepted | rejected | invalid | duplicate | failed
    family: str = ""
    title: str = ""
    concepts: List[str] = field(default_factory=list)
    parent_index: Optional[int] = None
    target: Optional[int] = None    # 0-based index of the requirement this attempt addressed
    score: Optional[float] = None
    reason: str = ""
    seconds: float = 0.0
    hypothesis: Optional[Hypothesis] = None


_HYP_FIELDS = ["id", "title", "family", "strategy", "iteration", "parent_id", "target", "concepts", "description",
               "postulates", "prediction", "refutation", "assumptions", "logical_flaws", "red_flags",
               "violated_hard_constraints", "violation_evidence", "numeric_flags", "confirmation_scores", "unverified_violations", "speculative_notes",
               "citations", "ai_estimate", "feasibility_score", "status", "needs_human_review"]


def hypothesis_to_dict(h: Hypothesis) -> dict:
    return {name: getattr(h, name) for name in _HYP_FIELDS}


@dataclass
class DiscoveryResult:
    goal: str
    config: DiscoveryConfig
    attempts: List[Attempt] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    requirements_source: str = "model"        # model | user
    finished_reason: str = ""
    started: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def accepted(self) -> List[Hypothesis]:
        found = [a.hypothesis for a in self.attempts if a.outcome == "accepted" and a.hypothesis]
        return sorted(found, key=lambda h: h.feasibility_score, reverse=True)

    def evaluated(self) -> List[Hypothesis]:
        return [a.hypothesis for a in self.attempts if a.hypothesis is not None]

    def near_misses(self, n: int = 3) -> List[Hypothesis]:
        rejected = [a.hypothesis for a in self.attempts if a.outcome == "rejected" and a.hypothesis]
        return sorted(rejected, key=lambda h: h.feasibility_score, reverse=True)[:n]

    def avg_seconds(self) -> float:
        done = [a.seconds for a in self.attempts if a.seconds]
        return sum(done) / len(done) if done else 0.0

    def requirement_coverage(self) -> List[dict]:
        rows = []
        for k, text in enumerate(self.requirements):
            mine = [a for a in self.attempts if a.target == k]
            scores = [a.score for a in mine if a.score is not None]
            rows.append({"requirement": k + 1, "text": text, "attempts": len(mine),
                         "accepted": sum(1 for a in mine if a.outcome == "accepted"),
                         "best_score": max(scores) if scores else None})
        return rows

    def exploration_log(self) -> List[dict]:
        return [{
            "n": a.index + 1, "strategy": a.strategy, "family": a.family, "title": a.title,
            "concepts": list(a.concepts), "parent": (a.parent_index + 1) if a.parent_index is not None else None,
            "target": (a.target + 1) if a.target is not None else None,
            "outcome": a.outcome, "score": a.score, "reason": a.reason, "seconds": round(a.seconds, 1),
        } for a in self.attempts]

    def to_dict(self) -> dict:
        return {
            "goal": self.goal, "started": self.started, "finished_reason": self.finished_reason,
            "config": asdict(self.config), "requirements": self.requirements,
            "requirements_source": self.requirements_source,
            "attempts": [{**log, "hypothesis": hypothesis_to_dict(a.hypothesis) if a.hypothesis else None}
                         for log, a in zip(self.exploration_log(), self.attempts)],
        }

    def save(self, path: str) -> str:
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False, default=str)
        return path


# ----------------------------------------------------------------------------------------------
# Pure helpers (deterministic, unit-tested)
# ----------------------------------------------------------------------------------------------
def keyword_set(text: str) -> set:
    return {w for w in re.findall(r"[a-z][a-z\-]{3,}", (text or "").lower()) if w not in _STOP}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def _norm_family(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (text or "").lower()).strip()


def consecutive_failures(attempts: List[Attempt]) -> int:
    n = 0
    for a in reversed(attempts):
        if a.outcome == "accepted":
            break
        n += 1
    return n


def root_index(attempt: Attempt, attempts: List[Attempt]) -> int:
    """Index of the first idea of a refinement chain (x -> x1 -> x2 all share the same root)."""
    seen = set()
    while attempt.parent_index is not None and attempt.index not in seen:
        seen.add(attempt.index)
        attempt = attempts[attempt.parent_index]
    return attempt.index


class DiscoveryEngine:
    def __init__(self, pool: Optional[AgentPool] = None, config: Optional[DiscoveryConfig] = None,
                 on_event: Optional[Callable[[str], None]] = print,
                 should_stop: Optional[Callable[[], bool]] = None):
        self.pool = pool or AgentPool()
        self.cfg = config or DiscoveryConfig()
        self.orchestrator = InvestigationOrchestrator(self.pool)
        self.sim = SimulationEngine(speculative=True)
        self.emit = on_event or (lambda msg: None)
        self.should_stop = should_stop or (lambda: False)
        self.rng = random.Random(self.cfg.seed)

    # ------------------------------------------------------------------ requirements (decomposition)
    def derive_requirements(self, analysis: GoalAnalysis, context: KnowledgeContext,
                            laws: Optional[List[str]] = None) -> List[str]:
        """
        Asks the model what must be ACHIEVED for the goal to work, then screens the answer in Python:
        every requirement needs a numeric target, must not be a limit that may not be broken, and must not
        restate a listed law. Unverified, model-derived.
        """
        laws = list(laws or UNIVERSAL_LAWS)
        prompt = (f"GOAL: {analysis.goal.description}\n"
                  "List the 3 to 4 EFFECTS that must be ACHIEVED for this goal to work, in terms of what physics would "
                  "have to do (not devices). Rules:\n"
                  "(1) every line needs a concrete numeric target with a unit, for example 'at least 1e-6 J/m^3 for 1 ms';\n"
                  "(2) do NOT list laws or limits that must not be broken (speed of light, conservation, entropy, material "
                  "limits): those are checked elsewhere;\n"
                  "(3) each effect must be something that does NOT happen by itself in nature.\n"
                  "Answer with one line per effect, exactly in this format:\nREQUIREMENT: <statement>\n")
        for attempt in range(2):
            raw = self.pool.inventor.perform_task(prompt, build_book(context), creative=True, temperature=0.3)
            accepted, rejected = split_requirements(raw, self.cfg.max_requirements, laws)
            if len(accepted) >= 2:
                return accepted
            why = "; ".join(f"'{t[:60]}...' ({r})" for t, r in rejected[:3]) or "the format was not followed"
            prompt += f"\nYour previous answer was rejected: {why}. Write 3 lines starting with 'REQUIREMENT:'."
        return []

    def pick_target(self, i: int, attempts: List[Attempt], requirements: List[str],
                    parent: Optional[Attempt]) -> Optional[int]:
        if not requirements:
            return None
        if parent is not None and parent.target is not None:
            return parent.target                      # a refinement keeps the target of its parent
        covered = {a.target for a in attempts if a.outcome == "accepted"}
        open_targets = [k for k in range(len(requirements)) if k not in covered] or list(range(len(requirements)))
        return open_targets[i % len(open_targets)]

    # ------------------------------------------------------------------ strategy scheduler
    def best_near_miss(self, attempts: List[Attempt]) -> Optional[Attempt]:
        counts: Dict[int, int] = {}
        for a in attempts:
            if a.strategy == "refine" and a.parent_index is not None:
                counts[a.parent_index] = counts.get(a.parent_index, 0) + 1
        per_root: Dict[int, int] = {}
        for a in attempts:
            if a.strategy == "refine":
                r = root_index(a, attempts)
                per_root[r] = per_root.get(r, 0) + 1
        pool = [a for a in attempts
                if a.outcome == "rejected" and a.hypothesis is not None and not a.hypothesis.violated_hard_constraints
                and (a.score or 0) >= self.cfg.near_miss_score
                and counts.get(a.index, 0) < self.cfg.max_refinements_per_parent
                and per_root.get(root_index(a, attempts), 0) < self.cfg.max_refinements_per_root]
        return max(pool, key=lambda a: a.score or 0) if pool else None

    def choose_strategy(self, i: int, attempts: List[Attempt]) -> Tuple[str, Optional[Attempt]]:
        if i == 0:
            return "explore", None
        near = self.best_near_miss(attempts)
        if near is not None and i % 3 == 2:
            return "refine", near
        if (self.cfg.allow_new_physics and consecutive_failures(attempts) >= self.cfg.postulate_after_failures
                and i % 4 == 3):
            return "postulate", None
        return ("recombine" if i % 2 == 1 else "explore"), None

    # ------------------------------------------------------------------ laws per attempt
    def boundaries_for(self, base: ConstraintContext, concepts: List[str], analysis: GoalAnalysis) -> ConstraintContext:
        laws = list(UNIVERSAL_LAWS)
        if (analysis.goal.domain == "biology") or any(concept_category(c) == "organism" for c in concepts):
            laws += BIOLOGY_LAWS
        merged = list(base.hard_constraints)
        for law in laws:
            line = f"MUST NOT VIOLATE: {law}"
            if line not in merged:
                merged.append(line)
        return ConstraintContext(goal_id=base.goal_id, hard_constraints=merged,
                                 soft_constraints=base.soft_constraints, evaluation_criteria=base.evaluation_criteria)

    # ------------------------------------------------------------------ prompts
    def format_spec(self, strategy: str) -> str:
        if strategy == "postulate" and self.cfg.allow_new_physics:
            quantity = ("NEW QUANTITY: <name> | SYMBOL: <1 to 4 characters> | DIMENSIONS: <SI units, e.g. kg m^2 s^-1> | "
                        "DEFINITION: <what it is> | EQUATION: <one equation that uses SYMBOL, e.g. dQ/dt = k * E * B> | "
                        "MAGNITUDE: <value or upper bound of its coupling constant, with SI units, e.g. < 1e-12 m^3 s^-2> | "
                        "COUPLING: <how it couples to known fields or matter> | REDUCES TO KNOWN PHYSICS WHEN: <condition "
                        "under which it vanishes> | DIFFERS FROM KNOWN QUANTITY BY: <only if its dimensions equal a known "
                        "quantity such as energy: how it differs>   (required: exactly 1 such line)\n"
                        "EXAMPLE of a well-formed line (unrelated topic, copy only the structure, never the content): "
                        "NEW QUANTITY: lattice twist density | SYMBOL: tau | DIMENSIONS: kg m^3 s^-1 | DEFINITION: the "
                        "torsional strain stored per unit length of a crystal | EQUATION: d(tau)/dt = k * E * B | MAGNITUDE: "
                        "< 1e-12 m^3 s^-2 | COUPLING: it couples to phonon momentum through a dimensionless constant | "
                        "REDUCES TO KNOWN PHYSICS WHEN: the coupling constant tends to zero\n")
        else:
            quantity = "(Do NOT postulate new quantities or laws in this attempt: use known physics only.)\n"
        return ("OUTPUT FORMAT (start each line with exactly these labels; no greetings, no markdown):\n"
                "TITLE: <short name>\n"
                "FAMILY: <2 to 5 words naming the core mechanism>\n"
                "MECHANISM: <at least 6 sentences: the step-by-step physical mechanism, with orders of magnitude "
                "(numbers and units) for the key quantities>\n"
                + quantity +
                "PREDICTION: <a measurable outcome with units and an expected numeric value or range>\n"
                "REFUTATION: <a specific measurement result that would prove this idea wrong>\n")

    def _tried_lines(self, attempts: List[Attempt], limit: int = 10) -> str:
        lines = []
        for a in attempts:
            if a.family:
                why = (a.reason or a.outcome)[:160].replace("\n", " ")
                lines.append(f"- {a.family} ({a.strategy}) -> {a.outcome}: {why}")
        return "\n".join(lines[-limit:]) if lines else "- nothing yet"

    def _barriers(self, attempts: List[Attempt], limit: int = 6) -> str:
        items = [f"- {a.family}: {(a.reason or '')[:200]}" for a in attempts if a.outcome == "rejected" and a.reason]
        return "\n".join(items[-limit:]) if items else "- (none recorded yet)"

    def build_prompt(self, strategy: str, analysis: GoalAnalysis, attempts: List[Attempt],
                     concepts: List[str], parent: Optional[Attempt], bnd: ConstraintContext,
                     requirements: Optional[List[str]] = None, target: Optional[int] = None) -> str:
        laws = "; ".join(h.replace("MUST NOT VIOLATE: ", "") for h in bnd.hard_constraints)
        head = f"GOAL: {analysis.goal.description}\n"
        if requirements and target is not None:
            head += ("TARGET REQUIREMENT (solve only this one; a complete device is NOT required): "
                     f"{requirements[target]}\n"
                     "Your PREDICTION must be a measurement showing that this requirement is met.\n")
        head += (f"LAWS THAT MUST STAY TRUE: {laws}\n"
                 f"ALREADY TRIED (never repeat these mechanism families):\n{self._tried_lines(attempts)}\n\n")
        if strategy == "recombine":
            body = ("STRATEGY: RECOMBINE. Build the mechanism by combining these seed concepts: "
                    + " + ".join(concepts) + ". Each seed must play a specific physical role in the mechanism. "
                    "The seeds may look unrelated: find the physical link between them.\n")
        elif strategy == "refine" and parent is not None and parent.hypothesis is not None:
            h = parent.hypothesis
            problems = list(h.logical_flaws) + list(h.red_flags) + list(h.speculative_notes)
            problems = problems or [parent.reason or "the score was below the threshold"]
            body = ("STRATEGY: REFINE. Improve the earlier candidate below. Keep its core idea but change what is needed "
                    "to fix ONLY these problems:\n- " + "\n- ".join(p[:240] for p in problems[:5]) + "\n"
                    "If a problem cannot be solved without abandoning the idea, choose a different mechanism instead.\n"
                    "Write the COMPLETE candidate again in the required format: describe every component in full and never refer "
                    "to the earlier version.\n"
                    f"EARLIER CANDIDATE:\n{h.description[:1800]}\n")
        elif strategy == "postulate":
            body = ("STRATEGY: POSTULATE. Earlier attempts hit these barriers:\n" + self._barriers(attempts) + "\n"
                    "Propose a mechanism that removes a barrier by postulating a NEW physical quantity or law. The "
                    "postulate must: (1) keep every law listed above true (total energy conservation included), "
                    "(2) have its own symbol and an equation someone could compute with, (3) give the size of its "
                    "coupling small enough not to contradict existing precision measurements, (4) say when it reduces "
                    "to known physics, and (5) predict something new and measurable that known physics does not "
                    "predict. Do not just rename an existing quantity.\n")
        else:
            body = ("STRATEGY: EXPLORE. Invent a mechanism from a family that is DIFFERENT from every family listed under "
                    "ALREADY TRIED. Prefer unusual but physically motivated approaches.\n")
        rules = ("RULES: Obey every law above. Do not claim the idea works; say what would show it fails. "
                 "Describe the WHOLE mechanism in full: never write 'as before', 'unchanged' or 'the earlier design'. "
                 "Do not restate these rules.\n\n")
        return head + body + rules + self.format_spec(strategy)

    # ------------------------------------------------------------------ novelty
    def is_duplicate(self, cand: Candidate, attempts: List[Attempt], parent: Optional[Attempt]) -> Optional[str]:
        fam = _norm_family(cand.family)
        kws = keyword_set(cand.family + " " + compose_description(cand))   # same text basis as the archive below
        lineage = set()
        if parent is not None:
            root = root_index(parent, attempts)
            lineage = {a.index for a in attempts if root_index(a, attempts) == root}
        for a in attempts:
            if not a.family:
                continue
            prev = a.hypothesis.description if a.hypothesis else a.family
            sim = jaccard(kws, keyword_set(a.family + " " + prev))
            if a.index in lineage:                    # parent, siblings and earlier versions of the same idea
                if sim >= 0.92:
                    return f"refinement is unchanged from attempt {a.index + 1}"
                continue
            if fam and fam == _norm_family(a.family):
                return f"same mechanism family as attempt {a.index + 1} ('{a.family}')"
            if sim >= self.cfg.novelty_threshold:
                return f"too similar to attempt {a.index + 1} (similarity {sim:.2f})"
        return None

    # ------------------------------------------------------------------ expert call
    def ask_expert(self, prompt: str, the_book: str, strategy: str) -> Tuple[Optional[Candidate], List[str], List[str]]:
        issues: List[str] = []
        for attempt in range(1 + self.cfg.format_retries):
            text = prompt if attempt == 0 else (
                prompt + "\n\nYour previous answer was rejected for these reasons: " + "; ".join(issues[:6])
                + ". Answer again using the exact format. MAGNITUDE must start with a number (for example '< 1e-12 m^3 s^-2'); "
                "EQUATION must contain '=' and the declared SYMBOL.")
            raw = self.pool.inventor.perform_task(text, the_book, creative=True,
                                                  temperature=self.cfg.expert_temperature)
            cand = parse_candidate(raw)
            issues, notes = validate_candidate(cand, self.cfg.allow_new_physics, strategy)
            if not issues:
                return cand, [], notes
        return None, issues, []

    # ------------------------------------------------------------------ one attempt
    def run_attempt(self, i: int, strategy: str, parent: Optional[Attempt], attempts: List[Attempt],
                    analysis: GoalAnalysis, context: KnowledgeContext, base_bnd: ConstraintContext,
                    requirements: Optional[List[str]] = None) -> Attempt:
        started = time.time()
        concepts = sample_concepts(self.rng, self.cfg.recombine_seeds, analysis.goal.description) \
            if strategy == "recombine" else []
        bnd = self.boundaries_for(base_bnd, concepts, analysis)
        target = self.pick_target(i, attempts, requirements or [], parent)
        target_text = requirements[target] if (requirements and target is not None) else ""
        attempt = Attempt(index=i, strategy=strategy, outcome="invalid", concepts=concepts,
                          parent_index=parent.index if parent else None, target=target)
        try:
            self._fill_attempt(attempt, i, strategy, parent, attempts, analysis, context, bnd,
                               requirements, target, target_text, concepts)
        finally:
            attempt.seconds = time.time() - started
        return attempt

    def _fill_attempt(self, attempt, i, strategy, parent, attempts, analysis, context, bnd,
                      requirements, target, target_text, concepts) -> None:
        prompt = self.build_prompt(strategy, analysis, attempts, concepts, parent, bnd, requirements, target)
        cand, issues, notes = self.ask_expert(prompt, build_book(context), strategy)
        if cand is None:
            attempt.reason = "invalid format: " + "; ".join(issues[:4])
            return
        attempt.family, attempt.title = cand.family, cand.title

        dup = self.is_duplicate(cand, attempts, parent)
        if dup:
            attempt.outcome, attempt.reason = "duplicate", dup
            return

        description = compose_description(cand)
        hyp = self.orchestrator.assess(description, analysis, context, bnd, speculative=True, target=target_text)
        if hyp is None:
            attempt.outcome, attempt.reason = "failed", "assessment collapsed (the Synthesizer returned no valid JSON)"
            return

        def decorate(h: Hypothesis) -> None:
            h.title, h.family, h.strategy, h.iteration = cand.title, cand.family, strategy, i + 1
            h.parent_id = parent.hypothesis.id if parent and parent.hypothesis else None
            h.concepts = concepts
            h.postulates = [format_postulate(p) for p in cand.postulates]
            h.prediction, h.refutation = cand.prediction, cand.refutation
            h.speculative_notes = list(h.speculative_notes) + notes
            h.target = target_text

        decorate(hyp)
        evaluated = self.sim.evaluate([hyp], bnd)[0]
        if evaluated.status == "active" and self.cfg.confirmations > 0:
            self._confirm(evaluated, description, analysis, context, bnd, target_text, decorate)
        attempt.hypothesis, attempt.score = evaluated, evaluated.feasibility_score
        if evaluated.status == "active":
            attempt.outcome = "accepted"
        else:
            attempt.outcome = "rejected"
            if evaluated.confirmation_scores and min(evaluated.confirmation_scores) < self.sim.MIN_VIABILITY:
                shown = ", ".join(f"{x * 100:.0f}%" for x in evaluated.confirmation_scores)
                reason = (f"Failed confirmation: independent re-assessments scored {shown} (all must reach "
                          f"{self.sim.MIN_VIABILITY * 100:.0f}%).")
                extra = [n for n in evaluated.speculative_notes if n.startswith("confirmation round")]
                if extra:
                    reason += " " + extra[0][:200]
            else:
                reason = self.sim.rejection_reason(evaluated)
                if evaluated.logical_flaws:
                    reason += " Flaw: " + evaluated.logical_flaws[0][:160]
            attempt.reason = reason

    def _confirm(self, first: Hypothesis, description: str, analysis: GoalAnalysis, context: KnowledgeContext,
                 bnd: ConstraintContext, target_text: str, decorate: Callable[[Hypothesis], None]) -> None:
        """
        Winner's curse: a candidate that reached the threshold was picked BECAUSE its noisy judgement came out
        high. It is re-assessed independently (higher judge temperature) and must reach the threshold every time.
        """
        scores = [first.feasibility_score]
        for k in range(self.cfg.confirmations):
            self.emit(f"    confirming {k + 1}/{self.cfg.confirmations} (independent re-assessment)...")
            again = self.orchestrator.assess(description, analysis, context, bnd, speculative=True, target=target_text,
                                             judge_temperature=self.cfg.confirmation_temperature)
            if again is None:
                continue
            decorate(again)
            again = self.sim.evaluate([again], bnd)[0]
            scores.append(again.feasibility_score)
            for flaw in again.logical_flaws:
                if flaw not in first.logical_flaws:
                    first.speculative_notes.append(f"confirmation round {k + 1} found: {flaw[:200]}")
        first.confirmation_scores = scores
        if min(scores) < self.sim.MIN_VIABILITY:
            first.status = "rejected"
            first.feasibility_score = min(scores)
            first.needs_human_review = True

    # ------------------------------------------------------------------ main loop
    def run(self, analysis: GoalAnalysis, context: KnowledgeContext, boundaries: ConstraintContext,
            save_path: Optional[str] = None, requirements: Optional[List[str]] = None) -> DiscoveryResult:
        result = DiscoveryResult(goal=analysis.goal.description, config=self.cfg)
        start = time.time()
        result.finished_reason = "iterations exhausted"

        user_reqs = [r.strip() for r in (requirements or []) if r and r.strip()]
        if user_reqs:
            result.requirements, result.requirements_source = user_reqs, "user"
            self.emit("Using the requirements supplied by the user:")
            for k, text in enumerate(user_reqs, 1):
                self.emit(f"    R{k}: {text}")
        elif self.cfg.use_requirements:
            self.emit("Deriving the physical requirements of the goal (model-derived, unverified)...")
            try:
                result.requirements = self.derive_requirements(analysis, context, boundaries.hard_constraints)
            except InferenceError as e:
                return self._llm_down(result, e, save_path)
            if result.requirements:
                for k, text in enumerate(result.requirements, 1):
                    self.emit(f"    R{k}: {text}")
            else:
                self.emit("    (no usable requirements; exploring the goal directly)")
        if save_path and result.requirements:
            result.save(save_path)

        def covered() -> bool:
            return bool(result.requirements) and all(
                any(a.outcome == "accepted" and a.target == k for a in result.attempts)
                for k in range(len(result.requirements)))

        for i in range(self.cfg.max_iterations):
            if len(result.accepted) >= self.cfg.target_count:
                result.finished_reason = "target reached"
                break
            if covered():
                result.finished_reason = "all requirements covered"
                break
            if self.should_stop():
                result.finished_reason = "stopped by user"
                break
            if self.cfg.max_minutes and (time.time() - start) > self.cfg.max_minutes * 60:
                result.finished_reason = "time limit reached"
                break

            strategy, parent = self.choose_strategy(i, result.attempts)
            self.emit(f"[{i + 1}/{self.cfg.max_iterations}] {strategy.upper()}"
                      + (f" (improving attempt {parent.index + 1})" if parent else ""))
            try:
                attempt = self.run_attempt(i, strategy, parent, result.attempts, analysis, context, boundaries,
                                           result.requirements)
            except InferenceError as e:
                return self._llm_down(result, e, save_path)
            result.attempts.append(attempt)

            label = attempt.outcome.upper() + (f" {attempt.score * 100:.0f}%" if attempt.score is not None else "")
            tag = f" [R{attempt.target + 1}]" if attempt.target is not None else ""
            self.emit(f"    -> {label}{tag}: {attempt.family or '(no valid candidate)'}"
                      + (f" | {attempt.reason[:230]}" if attempt.reason and attempt.outcome != "accepted" else ""))
            left = (self.cfg.max_iterations - len(result.attempts)) * result.avg_seconds() / 60
            self.emit(f"    (~{result.avg_seconds() / 60:.1f} min per attempt; up to ~{left:.0f} min left)")
            if save_path:
                result.save(save_path)
        else:
            if len(result.accepted) >= self.cfg.target_count:
                result.finished_reason = "target reached"
            elif covered():
                result.finished_reason = "all requirements covered"

        if save_path:
            result.save(save_path)
        return result

    def _llm_down(self, result: DiscoveryResult, error: InferenceError, save_path: Optional[str]) -> DiscoveryResult:
        """The local model stopped answering: keep the attempts made so far instead of losing the whole run."""
        result.finished_reason = f"local LLM unavailable: {error}"
        self.emit(f"[ERROR] {error}")
        if save_path:
            result.save(save_path)
        return result
