# HECE/src/hece/main.py
import os
import json
import uuid
from dotenv import load_dotenv

from hece.interpreter import GoalInterpreter
from hece.knowledge import KnowledgeEngine
from hece.constraints import ConstraintEngine
from hece.simulation import SimulationEngine
from hece.report import ReportGenerator
from hece.core.models.base import Hypothesis

# --- SPRINT 7: AGENTIC ORCHESTRATION ---
from hece.agents import AgentPool

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
    
    # --- SPRINT 2: KNOWLEDGE ENGINE ---
    print("\n📚 Status: Retrieving Scientific Context...")
    knowledge_engine = KnowledgeEngine()
    context = knowledge_engine.retrieve_context(analysis)
    
    # --- SPRINT 3: CONSTRAINT ENGINE ---
    print("\n🚧 Status: Establishing Scientific Boundaries...")
    constraint_engine = ConstraintEngine()
    boundaries = constraint_engine.process_constraints(analysis, context)
    
    # --- SPRINT 7: AGENTIC ORCHESTRATION (Substitui o Sprint 4) ---
    print("\n🤖 Status: Activating Multi-Agent Investigation...")
    pool = AgentPool()
    
    # 1. Expert proposes
    print("    -> [Expert] Proposing initial hypothesis...")
    task_propose = f"Propose a detailed scientific hypothesis for: {analysis.goal.description}"
    raw_hypothesis = pool.expert.perform_task(task_propose, str(context.domain_laws))
    
    # 2. Critic reviews
    print("    -> [Critic] Searching for constraint violations...")
    task_critic = f"Review this hypothesis: {raw_hypothesis}. Find any flaws based on these absolute rules: {boundaries.hard_constraints}"
    critique = pool.critic.perform_task(task_critic, "")
    
    # 3. Synthesizer merges
    print("    -> [Synthesizer] Merging critique and formatting output...")
    task_synth = f"Combine the hypothesis: {raw_hypothesis} and this critique: {critique}. Apply fixes if constraints were violated."
    
    # Forçar o Synthesizer a devolver JSON para não quebrar o pipeline
    json_format = """
    Format strictly as JSON ONLY:
    {"description": "str", "assumptions": ["str"], "required_conditions": ["str"], "feasibility_score": 0.5}
    Do not use markdown. Do not include explanations.
    """
    final_output = pool.synthesizer.perform_task(task_synth, json_format)
    
    # 4. Parse para o formato HECE (Pydantic)
    hypotheses = []
    try:
        # Caçador de JSON: Encontra exatamente onde abre e fecha o objeto
        start_idx = final_output.find('{')
        end_idx = final_output.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean_json = final_output[start_idx:end_idx+1]
            data = json.loads(clean_json)
            
            agent_hypothesis = Hypothesis(
                id=str(uuid.uuid4()),
                goal_id=analysis.goal.id,
                description=data.get("description", "No description provided."),
                assumptions=data.get("assumptions", []),
                required_conditions=data.get("required_conditions", []),
                feasibility_score=float(data.get("feasibility_score", 0.5)),
                confidence=0.5,
                status="speculative"
            )
            hypotheses.append(agent_hypothesis)
            
            print(f"\n[+] Generated 1 Agentic Hypothesis:")
            print(f"--- HYPOTHESIS 1 [{agent_hypothesis.status.upper()}] ---")
            print(f"Description: {agent_hypothesis.description}")
        else:
            raise ValueError("O LLM não retornou nenhum bloco de código JSON válido.")
            
    except Exception as e:
        print(f"\n[DEBUG] Synthesizer failed to output valid JSON: {final_output}")
        print(f"[ERROR] Parsing failed: {e}")

    # --- SPRINT 5: SIMULATION ENGINE ---
    print("\n🔬 Status: Running Hypothesis Evaluation & Simulation...")
    simulation_engine = SimulationEngine()
    evaluated_hypotheses = simulation_engine.evaluate(hypotheses, boundaries)
    
    print("\n[+] EVALUATION RESULTS:")
    for i, hyp in enumerate(evaluated_hypotheses, 1):
        status_icon = "🟢" if hyp.status == "active" else "🟡" if hyp.status == "speculative" else "🔴"
        print(f"    {status_icon} Hypothesis {i} -> New Status: [{hyp.status.upper()}]")
        print(f"       Final Feasibility: {hyp.feasibility_score * 100:.0f}%")

    # --- SPRINT 6: REPORT GENERATOR ---
    print("\n📑 Status: Compiling Final Scientific Report...")
    report_engine = ReportGenerator()
    final_report = report_engine.generate_report(analysis, context, boundaries, evaluated_hypotheses)
    
    saved_path = report_engine.export_to_markdown(final_report)
    print(f"\n[+] SUCCESS! Report saved to: {saved_path}")

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