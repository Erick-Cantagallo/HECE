# HECE/src/hece/hypothesis.py
import uuid
import json
import os
from typing import List
from hece.core.models.base import GoalAnalysis, KnowledgeContext, ConstraintContext, Hypothesis, Evidence
from hece.inference import InferenceEngine

class HypothesisEngine:
    """
    Generates structured scientific hypotheses using local LLM inference.
    """

    def __init__(self):
        # Initialize inference engine with config from .env
        model = os.getenv("MODEL_NAME", "llama3")
        self.inference = InferenceEngine(model_name=model)

    def _build_system_prompt(self, analysis: GoalAnalysis, knowledge: KnowledgeContext, constraints: ConstraintContext) -> str:
            prompt = f"""
            You are HECE, a strict scientific reasoning engine.
            GOAL: {analysis.goal.description}
            DOMAIN: {analysis.goal.domain}

            ABSOLUTE HARD CONSTRAINTS (DO NOT VIOLATE):
            {chr(10).join(constraints.hard_constraints)}

            EVALUATION CRITERIA:
            {chr(10).join(constraints.evaluation_criteria)}

            Respond in JSON format ONLY. 
            Example: {{"description": "text", "assumptions": ["a", "b"], "required_conditions": ["c"], "feasibility_score": 0.5}}
            """
            return prompt

    def generate_hypotheses(self, analysis: GoalAnalysis, knowledge: KnowledgeContext, constraints: ConstraintContext) -> List[Hypothesis]:
            """
            Uses local inference to generate a hypothesis, with strict JSON enforcement.
            """
            prompt = self._build_system_prompt(analysis, knowledge, constraints)
            
            # Add explicit instruction for the LLM to prevent conversational filler
            prompt += "\n\nIMPORTANT: Return ONLY the raw JSON object. Do not include any explanations, greetings, or markdown code blocks (```json). Start directly with '{' and end with '}'."
            
            response_text = self.inference.ask(prompt)
            
            try:
                # Clean markdown if present, despite the instructions
                clean_json = response_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                
                hypothesis = Hypothesis(
                    id=str(uuid.uuid4()),
                    goal_id=analysis.goal.id,
                    description=data.get("description", "No description provided."),
                    assumptions=data.get("assumptions", []),
                    required_conditions=data.get("required_conditions", []),
                    feasibility_score=float(data.get("feasibility_score", 0.5)),
                    confidence=0.5,
                    status="speculative"
                )
                return [hypothesis]
                
            except Exception as e:
                # DEBUG: If parsing fails, print the raw output so we can see what the model actually said
                print(f"\n[DEBUG] LLM raw response that failed to parse: {response_text}")
                print(f"[ERROR] JSON parsing error: {e}")
                return []