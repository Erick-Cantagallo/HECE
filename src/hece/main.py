# HECE/src/hece/main.py
import os
from dotenv import load_dotenv

from hece.interpreter import GoalInterpreter
from hece.knowledge import KnowledgeEngine
from hece.constraints import ConstraintEngine
from hece.simulation import SimulationEngine
from hece.agents import AgentPool, InvestigationOrchestrator
from hece.paper import PaperGenerator

load_dotenv()

def run_hece(goal_description: str):
    print("\n🧠 HECE ENGINE INITIALIZED")
    print("--------------------------")
    print("🔍 Status: Interpreting user goal...")

    # --- SPRINT 1: GOAL INTERPRETER ---
    interpreter = GoalInterpreter()
    analysis = interpreter.analyze(goal_description)
    
    print(f"\n[+] Goal ID: {analysis.goal.id}")
    domain_str = analysis.goal.domain or "general"
    print(f"[+] Domain Detected: {domain_str.upper()}")
    print(f"[+] Complexity Level: {analysis.goal.complexity_level}/10")
    
    # --- SPRINT 2 & 8: KNOWLEDGE ENGINE (RAG) ---
    print("\n📚 Status: Retrieving Scientific Context & Literature...")
    knowledge_engine = KnowledgeEngine()
    context = knowledge_engine.retrieve_context(analysis)
    
    # --- SPRINT 3: CONSTRAINT ENGINE ---
    print("\n🚧 Status: Establishing Scientific Boundaries...")
    constraint_engine = ConstraintEngine()
    boundaries = constraint_engine.process_constraints(analysis, context)
    
    # --- SPRINT 9 (Refactored): MULTI-AGENT ORCHESTRATION ---
    print("\n🤖 Status: Activating Multi-Agent Investigation (Target: 2 Hypotheses)...")
    pool = AgentPool()
    orchestrator = InvestigationOrchestrator(pool)
    hypotheses = orchestrator.investigate(analysis, context, boundaries, target_count=2)

    # --- SPRINT 5: SIMULATION ENGINE ---
    print("\n🔬 Status: Running Hypothesis Evaluation & Simulation...")
    simulation_engine = SimulationEngine()
    evaluated_hypotheses = simulation_engine.evaluate(hypotheses, boundaries)
    
    print("\n[+] EVALUATION RESULTS:")
    for i, hyp in enumerate(evaluated_hypotheses, 1):
        status_icon = "🟢" if hyp.status == "active" else "🔴"
        print(f"    {status_icon} Hypothesis {i} -> [{hyp.status.upper()}] (Feasibility: {hyp.feasibility_score * 100:.0f}%)")

    # --- SPRINT 9: PDF SCIENTIFIC PAPER GENERATOR ---
    print("\n📑 Status: Publishing Scientific Paper (PDF)...")
    pdf_path = PaperGenerator.generate_pdf(analysis, context, boundaries, evaluated_hypotheses)
    print(f"\n[+] SUCCESS! Paper published at: {pdf_path}")

    print("\n==========================================")
    print(" 🏁 HECE PIPELINE COMPLETED SUCCESSFULLY")
    print("==========================================\n")

if __name__ == "__main__":
    print("\n=== HECE - Hypothesis & Creativity Engine ===")
    user_input = input("Enter your scientific goal: ")
    if user_input.strip():
        run_hece(user_input)
    else:
        print("Error: Goal cannot be empty.")