# HECE/src/hece/agents.py
import os
import json
import uuid
from typing import List, Any
from hece.inference import InferenceEngine
from hece.core.models.base import Hypothesis, GoalAnalysis, KnowledgeContext, ConstraintContext

def _ensure_list(value: Any) -> List[str]:
    """Ensures that the LLM output is always a list of strings, preventing Pydantic ValidationErrors."""
    if isinstance(value, list):
        raw_list = [str(v) for v in value]
    elif isinstance(value, str):
        raw_list = [value]
    else:
        raw_list = []
        
    # FIX: The "None" Trap. Ignore strings where the AI conversationalizes an empty response.
    ignore_words = ["none", "none.", "n/a", "nil", "nothing", "empty", "no", "false"]
    clean_list = [item for item in raw_list if item.strip().lower() not in ignore_words]
    
    return clean_list

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
        generated_ideas = []  
        
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
                1. EXTREME DETAIL: You MUST write a comprehensive, deep thesis (at least 4 to 5 long paragraphs, 500+ words). Explain exactly HOW the mechanism works, WHY it is viable, and detail the step-by-step implementation.
                2. MATH FORMATTING: Provide explicit mathematical formulas using PLAIN TEXT ASCII ONLY (e.g., 'Force = mass * acceleration', 'A / B', 'd/dx'). DO NOT USE LATEX.
                """
                
                json_format = f"""
                CRITICAL INSTRUCTION: You are a strict data output API. You MUST return ONLY a valid JSON object.
                
                JSON RULES TO PREVENT PARSING CRASHES:
                1. ALL keys MUST be enclosed in double quotes.
                2. DO NOT use raw newlines. Use the literal characters '\\n' for paragraphs.
                3. DO NOT use unescaped double quotes inside strings. Use single quotes (') instead.
                4. ABSOLUTELY NO LATEX. DO NOT use backslashes (\\) or dollar signs ($) anywhere.
                
                JSON SCHEMA REQUIRED:
                {{
                    "description": "Write a massive, highly detailed scientific thesis here (500+ words). Use '\\n' for newlines. Explain the 'how' and 'why' extensively.",
                    "assumptions": ["List EVERY single unproven assumption here. DO NOT hide them in the text."],
                    "required_conditions": ["list of required conditions"],
                    "violated_hard_constraints": ["List EVERY absolute physics law broken (e.g., negative mass, faster-than-light). BE BRUTALLY HONEST. Do not ignore the Critic's warnings."],
                    "logical_flaws": ["List EVERY contradiction found by the Critic. DO NOT hide them."],
                    "citations": ["list of citations"]
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
                            # Auto-clean common LLM formatting errors
                            clean_json = clean_json.replace('\\', '\\\\').replace('\n', ' ')
                            data = json.loads(clean_json, strict=False)
                        
                        agent_hypothesis = Hypothesis(
                            id=str(uuid.uuid4()),
                            goal_id=analysis.goal.id,
                            description=data.get("description", "No description provided."),
                            # The _ensure_list function completely shields Pydantic from LLM data type hallucinations
                            assumptions=_ensure_list(data.get("assumptions", [])),
                            required_conditions=_ensure_list(data.get("required_conditions", [])),
                            violated_hard_constraints=_ensure_list(data.get("violated_hard_constraints", [])),
                            logical_flaws=_ensure_list(data.get("logical_flaws", [])),
                            citations=_ensure_list(data.get("citations", [])),
                            feasibility_score=0.0, 
                            confidence=0.5,
                            status="speculative"
                        )
                        hypotheses.append(agent_hypothesis)
                        generated_ideas.append(agent_hypothesis.description[:100])
                        success = True 
                    else:
                        raise ValueError("The LLM did not return a valid JSON format with {} brackets.")
                        
                except Exception as e:
                    # Provide feedback to the LLM for the next loop
                    error_feedback = f"\nCRITICAL ERROR PREVIOUSLY: Your last output failed with error: '{str(e)}'. You MUST fix the JSON formatting."
                    if attempt == max_retries:
                        print(f"[ERROR] Iteration {i+1} failed after {max_retries} attempts.")
                        print(f"[DEBUG RAW OUTPUT]:\n{final_output}\n")
                        
        return hypotheses