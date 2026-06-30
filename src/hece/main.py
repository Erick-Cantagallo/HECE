# HECE/src/hece/main.py
from hece.interpreter import GoalInterpreter

from hece.interpreter import GoalInterpreter
from hece.knowledge import KnowledgeEngine

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

    print("\n⚙️ Next step: Constraint Engine not implemented yet")
    print("--------------------------\n")

if __name__ == "__main__":
    print("\n=== HECE - Hypothesis & Creativity Engine ===")
    user_input = input("Enter your scientific goal: ")
    if user_input.strip():
        run_hece(user_input)
    else:
        print("Error: Goal cannot be empty.")