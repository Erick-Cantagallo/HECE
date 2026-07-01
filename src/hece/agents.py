# HECE/src/hece/agents.py
import os
import json
import uuid
from typing import List
from hece.inference import InferenceEngine
from hece.core.models.base import Hypothesis, GoalAnalysis, KnowledgeContext, ConstraintContext

class Agent:
    def __init__(self, name: str, role_description: str):
        self.name = name
        self.role = role_description
        self.inference = InferenceEngine(model_name=os.getenv("MODEL_NAME", "llama3"))

    def perform_task(self, task: str, context: str) -> str:
        prompt = f"""
        You are {self.name}. Your role is: {self.role}
        
        CONTEXT: {context}
        
        TASK: {task}
        
        Provide a concise, expert-level response.
        """
        return self.inference.ask(prompt)


class AgentPool:
    def __init__(self):
        self.expert = Agent("ScientificExpert", "You are an expert in the user's specific scientific domain. You provide rigorous, speculative hypotheses.")
        self.critic = Agent("ScientificCritic", "You are a harsh scientific critic. You challenge hypotheses for logical flaws and constraint violations.")
        self.synthesizer = Agent("Synthesizer", "You are a scientific writer. You combine expert insights and criticism into a final, structured summary.")


class InvestigationOrchestrator:
    """
    Coordinates the AgentPool to generate, critique, and synthesize hypotheses.
    Includes a self-healing Auto-Retry mechanism for JSON parsing failures.
    """
    def __init__(self, pool: AgentPool):
        self.pool = pool

    def investigate(self, analysis: GoalAnalysis, context: KnowledgeContext, boundaries: ConstraintContext, target_count: int = 2) -> List[Hypothesis]:
        hypotheses = []
        generated_ideas = []  # To prevent the LLM from repeating the same theory
        
        for i in range(target_count):
            print(f"\n   [Iteration {i+1}]")
            
            # 1. Expert proposes
            print("    -> [Expert] Proposing novel hypothesis...")
            avoid_prompt = f" Make it completely DIFFERENT from these previous ideas: {generated_ideas}" if generated_ideas else ""
            task_propose = f"Propose a detailed scientific hypothesis for: {analysis.goal.description}. Base it on the provided ArXiv literature if relevant.{avoid_prompt}"
            raw_hypothesis = self.pool.expert.perform_task(task_propose, str(context.known_facts))
            
            # 2. Critic reviews
            print("    -> [Critic] Searching for constraint violations...")
            task_critic = f"Review this hypothesis: {raw_hypothesis}. Find any flaws based on these absolute rules: {boundaries.hard_constraints}"
            critique = self.pool.critic.perform_task(task_critic, "")
            
            # 3. Synthesizer merges (With Auto-Retry)
            print("    -> [Synthesizer] Merging critique and extracting citations...")
            
            max_retries = 3
            attempt = 0
            success = False
            error_feedback = ""
            
            while attempt < max_retries and not success:
                attempt += 1
                if attempt > 1:
                    print(f"       [Retry {attempt}/{max_retries}] Asking LLM to fix JSON format...")
                    
                task_synth = f"""
                You are the lead scientific author. 
                Original Hypothesis: {raw_hypothesis}
                Critic's Review: {critique}
                
                TASK: Write the FINAL, improved scientific hypothesis. 
                Provide a deep, mathematically rigorous formulation. Detail the logical steps, 
                theoretical mechanics, and explicit mathematical equations.
                """
                
                json_format = f"""
                CRITICAL INSTRUCTION: You are a strict data output API. You MUST return ONLY a valid JSON object.
                
                JSON RULES TO PREVENT PARSING CRASHES:
                1. ALL keys MUST be enclosed in double quotes (e.g., "description").
                2. DO NOT use raw newlines (Enter key) inside strings. Use the literal characters '\\n' for paragraphs.
                3. DO NOT use unescaped double quotes inside strings. Use single quotes (') instead.
                4. DO NOT use backslashes (\\) for LaTeX math. Write math in plain text (e.g., write 'Delta' instead of '\\Delta').
                
                JSON SCHEMA REQUIRED:
                {{
                    "description": "Write a massive, detailed scientific thesis here. Use '\\n' for newlines. Use single quotes for emphasis.",
                    "assumptions": ["str"],
                    "required_conditions": ["str"],
                    "citations": ["str"],
                    "feasibility_score": 0.5
                }}
                {error_feedback}
                """
                
                final_output = self.pool.synthesizer.perform_task(task_synth, json_format)
                
                # 4. JSON Extraction & Safeguards
                try:
                    start_idx = final_output.find('{')
                    end_idx = final_output.rfind('}')
                    
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        clean_json = final_output[start_idx:end_idx+1]
                        
                        try:
                            data = json.loads(clean_json, strict=False)
                        except json.JSONDecodeError:
                            clean_json = clean_json.replace('\\', '\\\\').replace('\n', ' ')
                            data = json.loads(clean_json, strict=False)
                        
                        raw_score = float(data.get("feasibility_score", 0.5))
                        if raw_score > 1.0:
                            raw_score = raw_score / 10.0 if raw_score <= 10.0 else raw_score / 100.0
                        raw_score = min(max(raw_score, 0.0), 1.0) 
                        
                        agent_hypothesis = Hypothesis(
                            id=str(uuid.uuid4()),
                            goal_id=analysis.goal.id,
                            description=data.get("description", "No description provided."),
                            assumptions=data.get("assumptions", []),
                            required_conditions=data.get("required_conditions", []),
                            citations=data.get("citations", []),
                            feasibility_score=raw_score,
                            confidence=0.5,
                            status="speculative"
                        )
                        hypotheses.append(agent_hypothesis)
                        generated_ideas.append(agent_hypothesis.description[:100])
                        success = True # Escapes the retry loop
                        
                    else:
                        raise ValueError("The LLM did not return a valid JSON format with {} brackets.")
                        
                except Exception as e:
                    # Provide feedback to the LLM for the next loop
                    error_feedback = f"\nCRITICAL ERROR PREVIOUSLY: Your last output failed with error: '{str(e)}'. You MUST fix the JSON formatting."
                    if attempt == max_retries:
                        print(f"[ERROR] Iteration {i+1} failed after {max_retries} attempts.")
                        print(f"[DEBUG RAW OUTPUT]:\n{final_output}\n")
                        
        return hypotheses