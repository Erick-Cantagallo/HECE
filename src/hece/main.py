# HECE/src/hece/main.py
import os
from dotenv import load_dotenv

from hece.interpreter import GoalInterpreter
from hece.knowledge import KnowledgeEngine
from hece.constraints import ConstraintEngine
from hece.simulation import SimulationEngine
from hece.agents import AgentPool, InvestigationOrchestrator
from hece.paper import PaperGenerator
from hece.conclusion import build_conclusion

load_dotenv()

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
        
        # 3. Apply Rejection Sampling rules
        if broken_laws > 0:
            print("   ❌ [REJECTED]: Hypothesis violates fundamental physical laws.")
            continue
            
        if score < 65:
            print(f"   ❌ [REJECTED]: Viability ({score:.0f}%) is below the 65% minimum threshold.")
            continue
            
        # 4. If it survives the filters, add it to the final valid list
        print("   ✅ [ACCEPTED]: Hypothesis passed all strict viability thresholds!")
        evaluated_hypotheses.append(candidate)

    if not evaluated_hypotheses:
        print("\n[!] CRITICAL WARNING: Monte Carlo pipeline failed to find any viable hypotheses within the iteration limits.")

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

if __name__ == "__main__":
    print("\n=== HECE - Hypothesis & Creativity Engine ===")
    
    # 1. Ask for Project Name
    proj_name = input("Enter the Project Name (e.g., Project Orion): ")
    
    # 2. Ask for the Goal
    user_goal = input("Enter your scientific goal: ")
    
    # 3. Ask for Scalability (Number of Hypotheses)
    print("\n[COMPUTE WARNING]: Generating more hypotheses takes exponentially more time.")
    count_str = input("How many hypotheses do you want to generate? (e.g., 2, 5): ")
    
    try:
        target_hypotheses = int(count_str)
        if target_hypotheses <= 0:
            target_hypotheses = 1
    except ValueError:
        print("[!] Invalid number. Defaulting to 2 hypotheses.")
        target_hypotheses = 2
        
    if user_goal.strip() and proj_name.strip():
        run_hece(proj_name, user_goal, target_hypotheses)
    else:
        print("Error: Project name and Goal cannot be empty.")