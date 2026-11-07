# HECE/src/hece/conclusion.py
from typing import List
from hece.core.models.base import Hypothesis
from hece.simulation import SimulationEngine


def build_conclusion(pool, hypotheses: List[Hypothesis]) -> str:
    """
    Fully deterministic conclusion (no LLM), so it cannot endorse or invent anything.
    `pool` is kept only for call-site compatibility.
    """
    if not hypotheses:
        return "No valid hypotheses were generated to form a conclusion."

    engine = SimulationEngine()
    active = [h for h in hypotheses if h.status == "active"]
    lines = [f"{len(active)} of {len(hypotheses)} hypotheses passed the automated screening."]
    if active:
        lines.append("ACTIVE means: no verified law violation and a final score of at least "
                     f"{engine.MIN_VIABILITY * 100:.0f}%. It is NOT validation: nothing was tested experimentally "
                     "and every ACTIVE hypothesis requires expert review.")
    for i, h in enumerate(hypotheses, 1):
        if h.status == "active":
            est = h.ai_estimate if h.ai_estimate is not None else h.feasibility_score
            lines.append(f"Hypothesis {i} [ACTIVE] {h.feasibility_score * 100:.0f}%: AI estimate {est * 100:.0f}%, "
                         f"logical flaws {len(h.logical_flaws)}, assumptions {len(h.assumptions)}, "
                         f"red flags {len(h.red_flags)}.")
            for rf in h.red_flags:
                lines.append(f"  Red flag: {rf}")
        else:
            lines.append(f"Hypothesis {i} [REJECTED]: {engine.rejection_reason(h)}")
    return "\n".join(lines)


def _barrier_kind(h: Hypothesis) -> str:
    if h.violated_hard_constraints:
        return "verified law violation"
    if h.numeric_flags:
        return "arithmetic inconsistency (Python-verified)"
    if h.strategy and not (h.prediction.strip() and h.refutation.strip()):  # inventor-mode hypotheses only
        return "not falsifiable"
    if h.red_flags:
        return "deterministic red flags"
    if h.logical_flaws:
        return "grounded logical flaws"
    if len(h.assumptions) >= 3:
        return "too many unproven assumptions"
    return "AI viability estimate too low"


def build_discovery_conclusion(result) -> str:
    """Deterministic summary of an inventor-mode run (no LLM, so it cannot endorse anything)."""
    atts = result.attempts
    if not atts:
        return "No attempt was made."
    count = lambda outcome: sum(1 for a in atts if a.outcome == outcome)
    lines = [f"Exploration finished ({result.finished_reason}). {len(atts)} attempt(s): {count('accepted')} accepted, "
             f"{count('rejected')} rejected, {count('duplicate')} discarded as duplicates, "
             f"{count('invalid')} invalid format, {count('failed')} assessment failures."]

    mix = []
    for strategy in ("explore", "recombine", "refine", "postulate"):
        subset = [a for a in atts if a.strategy == strategy]
        if subset:
            mix.append(f"{strategy} {sum(1 for a in subset if a.outcome == 'accepted')}/{len(subset)}")
    lines.append("Accepted per strategy: " + ", ".join(mix) + ".")

    if result.avg_seconds():
        lines.append(f"Average time per attempt: {result.avg_seconds() / 60:.1f} min.")
    if result.requirements:
        lines.append("Requirements supplied by the user:" if getattr(result, "requirements_source", "model") == "user"
                     else "Requirements derived from the goal (model-derived, not verified):")
        for row in result.requirement_coverage():
            best = f"{row['best_score'] * 100:.0f}%" if row["best_score"] is not None else "n/a"
            lines.append(f"  R{row['requirement']}: {row['text'][:200]} -> {row['attempts']} attempt(s), "
                         f"{row['accepted']} accepted, best {best}")
        lines.append("A candidate for one requirement does not achieve the goal: the goal needs ALL requirements at once.")

    accepted = result.accepted
    if accepted:
        lines.append("ACTIVE means: no verified law violation, falsifiable, and a final score of at least 65%. "
                     "These are speculative candidates worth testing. They are NOT validated by experiment and "
                     "every one requires expert review.")
        for i, h in enumerate(accepted, 1):
            lines.append(f"Candidate {i}: {h.title or h.family} [{h.strategy}]{' for: ' + h.target[:120] if h.target else ''} {h.feasibility_score * 100:.0f}% "
                         f"(AI estimate {(h.ai_estimate if h.ai_estimate is not None else h.feasibility_score) * 100:.0f}%).")
            for p in h.postulates:
                lines.append(f"  Postulated: {p[:240]}")
            if h.confirmation_scores:
                lines.append("  Survived independent re-assessments: " + ", ".join(f"{x * 100:.0f}%" for x in h.confirmation_scores))
            lines.append(f"  Prediction: {h.prediction[:240]}")
            lines.append(f"  Refutation: {h.refutation[:240]}")
    else:
        lines.append("No candidate passed the screening. That is a valid result: it means the explored mechanisms "
                     "did not survive, not that the goal is impossible.")
        for i, h in enumerate(result.near_misses(3), 1):
            lines.append(f"Closest attempt {i}: {h.title or h.family} [{h.strategy}] {h.feasibility_score * 100:.0f}%.")

    kinds = {}
    for a in atts:
        if a.outcome == "rejected" and a.hypothesis is not None:
            kinds[_barrier_kind(a.hypothesis)] = kinds.get(_barrier_kind(a.hypothesis), 0) + 1
    if kinds:
        top = sorted(kinds.items(), key=lambda kv: -kv[1])
        lines.append("Most common barriers: " + "; ".join(f"{k} ({n})" for k, n in top) + ".")
    return "\n".join(lines)
