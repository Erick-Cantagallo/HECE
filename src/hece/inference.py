# HECE/src/hece/inference.py
import ollama


class InferenceError(RuntimeError):
    """The local LLM (Ollama) could not answer. The message explains how to fix it."""


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

        Raises InferenceError when the model cannot answer. Previously the error text
        was returned as if it were the model's answer, so the next agents silently
        "reviewed" an error message and the run ended with an empty report.
        """
        try:
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'user', 'content': prompt},
            ])
            return response['message']['content']
        except Exception as e:
            raise InferenceError(self._explain(e)) from e

    def _explain(self, error: Exception) -> str:
        if isinstance(error, ConnectionError):
            return (
                "Could not reach Ollama. Install it from https://ollama.com/download "
                "and make sure it is running (`ollama serve`)."
            )
        if getattr(error, "status_code", None) == 404:
            return (
                f"Model '{self.model_name}' is not available locally. "
                f"Download it with `ollama pull {self.model_name}` or change MODEL_NAME in your .env."
            )
        return f"Local LLM call failed ({type(error).__name__}): {error}"
