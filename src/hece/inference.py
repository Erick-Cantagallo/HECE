# HECE/src/hece/inference.py
import ollama
from typing import Optional

class InferenceEngine:
    """
    Handles communication with local LLMs (Ollama) to perform reasoning.
    All inference is local, private, and free.
    """
    
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name

    def ask(self, prompt: str) -> str:
        """
        Sends a prompt to the local model and returns the response.
        """
        try:
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'user', 'content': prompt},
            ])
            return response['message']['content']
        except Exception as e:
            return f"Error connecting to local LLM: {str(e)}"