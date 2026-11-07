# HECE/src/hece/benchmark.py
"""
Screening benchmark: does the score separate hypotheses that respect known laws from ones that break them?

Each case is a FIXED hypothesis text with a verdict known in advance ('pass' or 'fail'). It is scored by the same
Critic + Synthesizer + SimulationEngine used by run_hece, without literature retrieval (so results do not depend
on arXiv). Nothing is generated: the benchmark measures the filter, not the inventor.

    hece-benchmark                        # benchmarks/screening.json, 1 repetition
    hece-benchmark --repeat 3 --only good-heat-pump
"""
import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

from dotenv import load_dotenv

from hece import __version__
from hece.agents import AgentPool, InvestigationOrchestrator
from hece.constraints import ConstraintEngine
from hece.inference import DEFAULT_MODEL, InferenceError
from hece.interpreter import GoalInterpreter
from hece.pipeline import offline_context
from hece.simulation import SimulationEngine

DEFAULT_CASES = os.path.join("benchmarks", "screening.json")


@dataclass
class Case:
    id: str
    expected: str  # 'pass' or 'fail'
    goal: str
    hypothesis: str
    why: str = ""


@dataclass
class CaseResult:
    id: str
    expected: str
    run: int
    status: str  # 'active', 'rejected' or 'failed' (the Synthesizer produced no valid JSON)
    score: float = 0.0
    ai_estimate: Optional[float] = None
    verified_violations: List[str] = field(default_factory=list)
    logical_flaws: int = 0
    assumptions: int = 0
    unverified_accusations: int = 0
    red_flags: List[str] = field(default_factory=list)
    numeric_flags: List[str] = field(default_factory=list)
    reason: str = ""
    seconds: float = 0.0

    @property
    def correct(self) -> bool:
        return (self.status == "active") == (self.expected == "pass")


def load_cases(path: str = DEFAULT_CASES) -> List[Case]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    cases = [Case(**{k: c[k] for k in ("id", "expected", "goal", "hypothesis", "why") if k in c}) for c in data["cases"]]
    for c in cases:
        if c.expected not in ("pass", "fail"):
            raise ValueError(f"case {c.id}: expected must be 'pass' or 'fail', got {c.expected!r}")
    return cases


def screen(case: Case, orchestrator: InvestigationOrchestrator, sim: SimulationEngine, run: int = 1) -> CaseResult:
    """Scores one fixed hypothesis exactly like run_hece does (minus literature retrieval)."""
    started = time.time()
    analysis = GoalInterpreter().analyze(case.goal)
    context = offline_context(analysis)
    boundaries = ConstraintEngine().process_constraints(analysis, context)

    hyp = orchestrator.assess(case.hypothesis, analysis, context, boundaries)
    if hyp is None:
        return CaseResult(case.id, case.expected, run, "failed", reason="the Synthesizer returned no valid JSON",
                          seconds=time.time() - started)
    hyp = sim.evaluate([hyp], boundaries)[0]
    return CaseResult(
        case.id, case.expected, run, hyp.status, score=hyp.feasibility_score, ai_estimate=hyp.ai_estimate,
        verified_violations=list(hyp.violated_hard_constraints), logical_flaws=len(hyp.logical_flaws),
        assumptions=len(hyp.assumptions), unverified_accusations=len(hyp.unverified_violations),
        red_flags=list(hyp.red_flags), numeric_flags=list(hyp.numeric_flags),
        reason="" if hyp.status == "active" else sim.rejection_reason(hyp), seconds=time.time() - started)


def summarize(results: List[CaseResult]) -> dict:
    """Confusion counts plus the score ranges of each group (to see whether ANY threshold would separate them)."""
    threshold = SimulationEngine().MIN_VIABILITY
    scored = [r for r in results if r.status != "failed"]
    good = [r.score for r in scored if r.expected == "pass"]
    bad = [r.score for r in scored if r.expected == "fail"]
    passed_good = sum(1 for r in scored if r.expected == "pass" and r.status == "active")
    passed_bad = sum(1 for r in scored if r.expected == "fail" and r.status == "active")
    return {
        "runs": len(results), "failed": len(results) - len(scored),
        "good_passed": passed_good, "good_total": len(good),
        "bad_passed": passed_bad, "bad_total": len(bad),
        "accuracy": round(sum(r.correct for r in scored) / len(scored), 3) if scored else None,
        "good_scores": sorted(good), "bad_scores": sorted(bad),
        # > 0 means some threshold would separate every good case from every bad case
        "separation_margin": round(min(good) - max(bad), 3) if good and bad else None,
        "threshold": threshold,
    }


def format_report(results: List[CaseResult], summary: dict) -> str:
    lines = [f"{'case':32} {'expected':8} {'status':9} {'score':>5} {'AI':>4}  flaws assum unver red num  verified"]
    for r in results:
        ai = f"{r.ai_estimate * 100:.0f}" if r.ai_estimate is not None else "-"
        mark = "ok " if r.correct else "BAD"
        lines.append(f"{mark} {r.id[:28]:28} {r.expected:8} {r.status:9} {r.score * 100:5.0f} {ai:>4}  "
                     f"{r.logical_flaws:5} {r.assumptions:5} {r.unverified_accusations:5} {len(r.red_flags):3} "
                     f"{len(r.numeric_flags):3}  {'; '.join(r.verified_violations)[:60]}")
    s = summary
    lines += ["",
              f"Good hypotheses accepted: {s['good_passed']}/{s['good_total']}   "
              f"Bad hypotheses accepted: {s['bad_passed']}/{s['bad_total']}   "
              f"Accuracy: {s['accuracy']}   Assessment failures: {s['failed']}",
              f"Good scores: {[round(x, 2) for x in s['good_scores']]}",
              f"Bad scores:  {[round(x, 2) for x in s['bad_scores']]}"]
    if s["separation_margin"] is not None:
        lines.append(("Some threshold separates the groups (margin %.2f)." if s["separation_margin"] > 0
                      else "No threshold separates the groups (overlap %.2f).") % abs(s["separation_margin"]))
    return "\n".join(lines)


def run_benchmark(cases: List[Case], repeat: int = 1, on_event: Callable[[str], None] = print,
                  orchestrator: Optional[InvestigationOrchestrator] = None) -> List[CaseResult]:
    orchestrator = orchestrator or InvestigationOrchestrator(AgentPool())
    sim = SimulationEngine()
    results = []
    for run in range(1, repeat + 1):
        for case in cases:
            on_event(f"[run {run}/{repeat}] {case.id} (expected: {case.expected})")
            r = screen(case, orchestrator, sim, run)
            on_event(f"    -> {r.status.upper()} {r.score * 100:.0f}% ({r.seconds:.0f} s)"
                     + ("" if r.correct else "   <-- WRONG VERDICT"))
            results.append(r)
    return results


def main(argv=None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="hece-benchmark",
                                     description="Measure whether HECE's screening separates hypotheses with a known verdict.")
    parser.add_argument("--cases", default=DEFAULT_CASES, help=f"JSON file with the cases (default: {DEFAULT_CASES})")
    parser.add_argument("--repeat", type=int, default=1, help="score every case this many times (the model is sampled)")
    parser.add_argument("--only", action="append", help="run only this case id (repeat the option for several)")
    parser.add_argument("--out", default=None, help="where to save the JSON results (default: runs/benchmark_<time>.json)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    if args.only:
        cases = [c for c in cases if c.id in args.only]
        if not cases:
            print("Error: no case matches --only.", file=sys.stderr)
            return 1

    model = os.getenv("MODEL_NAME", DEFAULT_MODEL)
    print(f"HECE {__version__} screening benchmark: {len(cases)} case(s) x {args.repeat}, model {model}\n")
    try:
        results = run_benchmark(cases, max(1, args.repeat))
    except InferenceError as exc:
        print(f"\n[ERROR] Benchmark stopped: {exc}", file=sys.stderr)
        return 1

    summary = summarize(results)
    print("\n" + format_report(results, summary))

    out = args.out or os.path.join("runs", f"benchmark_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"version": __version__, "model": model, "cases_file": args.cases, "summary": summary,
                   "results": [asdict(r) for r in results]}, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Results: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
