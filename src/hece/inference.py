# HECE/src/hece/inference.py
import time
import ollama
from typing import Optional


# Chosen with hece-benchmark (benchmarks/RESULTS.md): it let no law-breaking case through, llama3 let 3 of 11.
DEFAULT_MODEL = "qwen3:4b-instruct-2507-q4_K_M"


class InferenceError(RuntimeError):
    """The local LLM (Ollama) could not answer. The message explains how to fix it."""


class InferenceEngine:
    """
    Handles communication with local LLMs (Ollama) to perform reasoning.
    All inference is local, private, and free.
    """

    SERVER_ERROR_RETRIES = 1
    RETRY_DELAY_SECONDS = 5

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name

    def ask(self, prompt: str, temperature: Optional[float] = None) -> str:
        """
        Sends a prompt to the local model and returns the response.
        `temperature` (optional): higher values make the model more inventive (used by the inventor agent).

        Raises InferenceError when the model cannot answer. Previously the error text
        was returned as if it were the model's answer, so the next agents silently
        "reviewed" an error message and the run ended with an empty report.
        """
        kwargs = {"options": {"temperature": temperature}} if temperature is not None else {}
        for attempt in range(1 + self.SERVER_ERROR_RETRIES):
            try:
                response = ollama.chat(model=self.model_name, messages=[
                    {'role': 'user', 'content': prompt},
                ], **kwargs)
                return response['message']['content']
            except Exception as e:
                # A 5xx usually means the model failed to load (e.g. a memory spike): worth one more try.
                if (getattr(e, "status_code", None) or 0) >= 500 and attempt < self.SERVER_ERROR_RETRIES:
                    time.sleep(self.RETRY_DELAY_SECONDS)
                    continue
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
