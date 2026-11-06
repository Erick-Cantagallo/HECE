# HECE/src/hece/main.py
import argparse
import sys
from typing import Optional, Sequence

from dotenv import load_dotenv

from hece.interpreter import GoalInterpreter
from hece.knowledge import KnowledgeEngine
from hece.constraints import ConstraintEngine
from hece.simulation import SimulationEngine
from hece.agents import AgentPool, InvestigationOrchestrator
from hece.inference import InferenceError
from hece.paper import PaperGenerator

load_dotenv()

DEFAULT_PROJECT = "Investigation"
DEFAULT_HYPOTHESES = 2

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

    print(f"\n🤖 Status: Activating Multi-Agent Investigation (Target: {target_count} Hypotheses)...")
    pool = AgentPool()
    orchestrator = InvestigationOrchestrator(pool)
    hypotheses = orchestrator.investigate(analysis, context, boundaries, target_count=target_count)

    print("\n🔬 Status: Running Hypothesis Evaluation & Simulation...")
    simulation_engine = SimulationEngine()
    evaluated_hypotheses = simulation_engine.evaluate(hypotheses, boundaries)

    print("\n[+] EVALUATION RESULTS:")
    for i, hyp in enumerate(evaluated_hypotheses, 1):
        status_icon = "🟢" if hyp.status == "active" else "🔴"
        print(f"    {status_icon} Hypothesis {i} -> [{hyp.status.upper()}] (Feasibility: {hyp.feasibility_score * 100:.0f}%)")

    # --- SPRINT 10 (Credibility Update): DEEP CONCLUSION SYNTHESIS ---
    print("\n🧠 Status: Synthesizing deep scientific conclusion...")
    if evaluated_hypotheses:
        hypotheses_text = " | ".join([f"Hypothesis {i+1}: {h.description} (Score: {h.feasibility_score})" for i, h in enumerate(evaluated_hypotheses)])
        conclusion_prompt = f"""
        Analyze the following {len(evaluated_hypotheses)} evaluated hypotheses: {hypotheses_text}.
        Write a comprehensive, deep comparative scientific conclusion.
        Which approach is most promising? What are the critical roadblocks or physics violations?
        """
        deep_conclusion = pool.synthesizer.perform_task(conclusion_prompt, "Write 2 to 3 insightful paragraphs. DO NOT use markdown bolding (**) or quotes.")
    else:
        deep_conclusion = "No valid hypotheses were generated to form a conclusion."

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
