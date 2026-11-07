# HECE/src/hece/main.py
import argparse
import sys
from typing import Optional, Sequence

from dotenv import load_dotenv

from hece import __version__
from hece.interpreter import GoalInterpreter
from hece.knowledge import KnowledgeEngine
from hece.constraints import ConstraintEngine
from hece.simulation import SimulationEngine
from hece.agents import AgentPool, InvestigationOrchestrator
from hece.inference import InferenceError
from hece.paper import PaperGenerator
from hece.conclusion import build_conclusion

load_dotenv()

DEFAULT_PROJECT = "Investigation"
DEFAULT_HYPOTHESES = 2
NEAR_MISSES_SHOWN = 3

def run_hece(project_name: str, goal_description: str, target_count: int):
    print(f"\n🧠 HECE ENGINE INITIALIZED - PROJECT: {project_name.upper()}")
    print("--------------------------------------------------")
    print("🔍 Status: Interpreting user goal...")

    interpreter = GoalInterpreter()
    analysis = interpreter.analyze(goal_description)
    
    print(f"\n[+] Goal ID: {analysis.goal.id}")
    domain_str = analysis.goal.domain or "general"
    print(f"[+] Domain Detected: {domain_str.upper()}")
    print(f"[+] Complexity Level: {analysis.goal.complexity_level}/10")
    
    print("\n📚 Status: Retrieving Scientific Context & Literature...")
    knowledge_engine = KnowledgeEngine()
    context = knowledge_engine.retrieve_context(analysis)
    
    print("\n🚧 Status: Establishing Scientific Boundaries...")
    constraint_engine = ConstraintEngine()
    boundaries = constraint_engine.process_constraints(analysis, context)
    
    # Initialize the core engines before the loop
    pool = AgentPool()
    orchestrator = InvestigationOrchestrator(pool)
    simulation_engine = SimulationEngine()
    
    print(f"\n🤖 Status: Activating Multi-Agent Investigation (Target: {target_count} Valid Hypotheses)...")
    print("🎲 [MONTE CARLO SAMPLING ACTIVE: Minimum 65% Viability & 0 Broken Laws]")
    
    # --- MONTE CARLO (REJECTION SAMPLING) LOOP ---
    evaluated_hypotheses = []
    rejected_hypotheses = []  # kept so the report can still show the best near misses
    attempts = 0
    # Safeguard against infinite loops: we allow 4 attempts per requested hypothesis
    max_attempts = target_count * 4 

    while len(evaluated_hypotheses) < target_count and attempts < max_attempts:
        attempts += 1
        print(f"\n   === Monte Carlo Attempt {attempts}/{max_attempts} ===")
        
        # 1. Generate exactly 1 hypothesis candidate
        hypotheses_batch = orchestrator.investigate(analysis, context, boundaries, target_count=1)
        
        if not hypotheses_batch:
            print("   [!] Generation failed due to Agent collapse. Retrying...")
            continue
            
        # 2. Evaluate the candidate immediately
        evaluated_batch = simulation_engine.evaluate(hypotheses_batch, boundaries)
        candidate = evaluated_batch[0]
        
        # Extract metrics for the deterministic check
        score = candidate.feasibility_score * 100
        broken_laws = len(candidate.violated_hard_constraints)
        
        print(f"   📊 [Simulation] Score: {score:.0f}% | Broken Laws: {broken_laws}")
        
        # 3. Apply Rejection Sampling rules (the SimulationEngine already set the status)
        if candidate.status != "active":
            print(f"   ❌ [REJECTED]: {simulation_engine.rejection_reason(candidate)}")
            rejected_hypotheses.append(candidate)
            continue

        # 4. If it survives the filters, add it to the final valid list
        print("   ✅ [ACCEPTED]: Hypothesis passed all strict viability thresholds!")
        evaluated_hypotheses.append(candidate)

    if not evaluated_hypotheses:
        print("\n[!] CRITICAL WARNING: Monte Carlo pipeline failed to find any viable hypotheses within the iteration limits.")
        # Show the best near misses (clearly marked REJECTED, with the reason) instead of an empty report.
        evaluated_hypotheses = sorted(rejected_hypotheses, key=lambda h: h.feasibility_score, reverse=True)[:NEAR_MISSES_SHOWN]

    print("\n[+] EVALUATION RESULTS:")
    for i, hyp in enumerate(evaluated_hypotheses, 1):
        status_icon = "🟢" if hyp.status == "active" else "🔴"
        print(f"    {status_icon} Hypothesis {i} -> [{hyp.status.upper()}] (Feasibility: {hyp.feasibility_score * 100:.0f}%)")

    # --- SPRINT 10 (Credibility Update): DEEP CONCLUSION SYNTHESIS ---
    print("\n🧠 Status: Synthesizing deep scientific conclusion...")
    deep_conclusion = build_conclusion(pool, evaluated_hypotheses)

    print("\n📑 Status: Publishing Scientific Paper (PDF)...")
    pdf_path = PaperGenerator.generate_pdf(project_name, analysis, context, boundaries, evaluated_hypotheses, deep_conclusion)
    print(f"\n[+] SUCCESS! Paper published at: {pdf_path}")

    print("\n==========================================")
    print(" 🏁 HECE PIPELINE COMPLETED SUCCESSFULLY")
    print("==========================================\n")

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hece",
        description="HECE - Hypothesis & Creativity Engine: structured scientific investigation with local LLMs.",
        epilog='Example: hece "How could a battery store more energy per kilogram?" -p Orion -n 3',
    )
    parser.add_argument("goal", nargs="?", help="scientific goal to investigate (omit it to answer the prompts interactively)")
    parser.add_argument("-p", "--project", help=f"project name used in the PDF (default: {DEFAULT_PROJECT})")
    parser.add_argument("-n", "--hypotheses", type=int, help=f"how many hypotheses to generate (default: {DEFAULT_HYPOTHESES})")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser

def _ask_hypothesis_count() -> int:
    print("\n[COMPUTE WARNING]: Generating more hypotheses takes exponentially more time.")
    count_str = input("How many hypotheses do you want to generate? (e.g., 2, 5): ")
    try:
        return max(1, int(count_str))
    except ValueError:
        print(f"[!] Invalid number. Defaulting to {DEFAULT_HYPOTHESES} hypotheses.")
        return DEFAULT_HYPOTHESES

def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command line entry point (`hece`, `python -m hece` or `python -m hece.main`)."""
    args = _build_parser().parse_args(argv)
    print("\n=== HECE - Hypothesis & Creativity Engine ===")

    try:
        if args.goal is None:
            # Interactive mode: same prompts HECE always had.
            project = args.project or input("Enter the Project Name (e.g., Project Orion): ")
            goal = input("Enter your scientific goal: ")
            count = max(1, args.hypotheses) if args.hypotheses is not None else _ask_hypothesis_count()
        else:
            # One-shot mode: no prompts, ready for scripts.
            project = args.project or DEFAULT_PROJECT
            goal = args.goal
            count = max(1, args.hypotheses) if args.hypotheses is not None else DEFAULT_HYPOTHESES
    except (EOFError, KeyboardInterrupt):
        print("\n[!] Aborted.", file=sys.stderr)
        return 1

    if not goal.strip() or not project.strip():
        print("Error: Project name and Goal cannot be empty.", file=sys.stderr)
        return 1

    try:
        run_hece(project, goal, count)
    except InferenceError as exc:
        print(f"\n[ERROR] HECE stopped: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())