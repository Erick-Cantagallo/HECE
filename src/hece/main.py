# HECE/src/hece/main.py
from hece.hypothesis import HypothesisEngine
from hece.interpreter import GoalInterpreter
from hece.knowledge import KnowledgeEngine
from hece.constraints import ConstraintEngine
from hece.simulation import SimulationEngine
from hece.report import ReportGenerator
from dotenv import load_dotenv
load_dotenv()
import os


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
    print(f"[+] Keywords Extracted: {', '.join(analysis.keywords)}")
    
    if analysis.extracted_constraints:
        print("\n[!] Initial Constraints Identified:")
        for constraint in analysis.extracted_constraints:
            print(f"    - [{constraint.type}] {constraint.description} (Strictness: {constraint.strictness}/10)")
    else:
        print("\n[-] No initial constraints detected.")


    # --- SPRINT 2: KNOWLEDGE ENGINE ---
    print("\n📚 Status: Retrieving Scientific Context...")
    knowledge_engine = KnowledgeEngine()
    context = knowledge_engine.retrieve_context(analysis)
    
    print("\n[+] Domain Laws Injected (Axioms):")
    for law in context.domain_laws:
        print(f"    - {law}")
        
    if context.current_limitations:
        print("\n[!] Known Scientific Limitations:")
        for limitation in context.current_limitations:
            print(f"    - {limitation}")


    # --- SPRINT 3: CONSTRAINT ENGINE ---
    print("\n🚧 Status: Establishing Scientific Boundaries...")
    constraint_engine = ConstraintEngine()
    boundaries = constraint_engine.process_constraints(analysis, context)
    
    print("\n[+] HARD CONSTRAINTS (Absolute Rules):")
    for hc in boundaries.hard_constraints:
        print(f"    ❌ {hc}")
        
    if boundaries.soft_constraints:
        print("\n[+] SOFT CONSTRAINTS (Preferences):")
        for sc in boundaries.soft_constraints:
            print(f"    ⚠️ {sc}")
            
    print("\n[+] EVALUATION CRITERIA (Success Metrics):")
    for crit in boundaries.evaluation_criteria:
        print(f"    ✅ {crit}")


    # --- SPRINT 4: HYPOTHESIS ENGINE ---
    print("\n💡 Status: Generating Scientific Hypotheses...")
    hypothesis_engine = HypothesisEngine()
    hypotheses = hypothesis_engine.generate_hypotheses(analysis, context, boundaries)
    
    print(f"\n[+] Generated {len(hypotheses)} Hypothesis/Hypotheses:")
    for i, hyp in enumerate(hypotheses, 1):
        print(f"\n--- HYPOTHESIS {i} [{hyp.status.upper()}] ---")
        print(f"ID: {hyp.id}")
        print(f"Description: {hyp.description}")
        print(f"Feasibility: {hyp.feasibility_score * 100}% | Confidence: {hyp.confidence * 100}%")
        
        if hyp.assumptions:
            print("Key Assumptions:")
            for assumption in hyp.assumptions:
                print(f"  - {assumption}")
                
        if hyp.supporting_evidence:
            print("Supporting Evidence:")
            for ev in hyp.supporting_evidence:
                print(f"  - {ev.description} (Source: {ev.source}, Reliability: {ev.reliability})")


    # --- SPRINT 5: SIMULATION ENGINE ---
    print("\n🔬 Status: Running Hypothesis Evaluation & Simulation...")
    simulation_engine = SimulationEngine()
    evaluated_hypotheses = simulation_engine.evaluate(hypotheses, boundaries)
    
    print("\n[+] EVALUATION RESULTS:")
    for i, hyp in enumerate(evaluated_hypotheses, 1):
        status_icon = "🟢" if hyp.status == "active" else "🟡" if hyp.status == "speculative" else "🔴"
        # .0f format stops floating point errors (e.g., 55.000000001%)
        print(f"    {status_icon} Hypothesis {i} -> New Status: [{hyp.status.upper()}]")
        print(f"       Final Feasibility: {hyp.feasibility_score * 100:.0f}%")


    # --- SPRINT 6: REPORT GENERATOR ---
    print("\n📑 Status: Compiling Final Scientific Report...")
    report_engine = ReportGenerator()
    final_report = report_engine.generate_report(analysis, context, boundaries, evaluated_hypotheses)
    
    # Save to the physical "reports/" folder
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