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