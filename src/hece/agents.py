# HECE/src/hece/agents.py
from hece.inference import InferenceEngine
import os

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

# Definição dos nossos especialistas
class AgentPool:
    def __init__(self):
        self.expert = Agent("ScientificExpert", "You are an expert in the user's specific scientific domain. You provide rigorous, speculative hypotheses.")
        self.critic = Agent("ScientificCritic", "You are a harsh scientific critic. You challenge hypotheses for logical flaws and constraint violations.")
        self.synthesizer = Agent("Synthesizer", "You are a scientific writer. You combine expert insights and criticism into a final, structured summary.")