# HECE/tests/unit/test_inference.py
import pytest
from unittest.mock import patch

from hece.inference import InferenceEngine, InferenceError


@patch("hece.inference.ollama.chat")
def test_ask_returns_the_model_answer(mock_chat):
    mock_chat.return_value = {"message": {"content": "42"}}

    assert InferenceEngine(model_name="llama3").ask("Meaning of life?") == "42"
    mock_chat.assert_called_once_with(
        model="llama3",
        messages=[{"role": "user", "content": "Meaning of life?"}],
    )


@patch("hece.inference.ollama.chat", side_effect=ConnectionError("connection refused"))
def test_ask_explains_when_ollama_is_not_running(_chat):
    with pytest.raises(InferenceError, match="ollama serve"):
        InferenceEngine().ask("hi")


@patch("hece.inference.ollama.chat")
def test_ask_explains_when_the_model_is_missing(mock_chat):
    class ModelNotFound(Exception):
        status_code = 404  # same shape as ollama.ResponseError

    mock_chat.side_effect = ModelNotFound("model not found")

    with pytest.raises(InferenceError, match="ollama pull mistral"):
        InferenceEngine(model_name="mistral").ask("hi")


@patch("hece.inference.ollama.chat", side_effect=ValueError("boom"))
def test_ask_wraps_unexpected_errors_and_keeps_the_cause(_chat):
    with pytest.raises(InferenceError, match=r"ValueError.*boom") as excinfo:
        InferenceEngine().ask("hi")

    assert isinstance(excinfo.value.__cause__, ValueError)


class ServerError(Exception):
    status_code = 500  # same shape as ollama.ResponseError when the model fails to load


@patch("hece.inference.time.sleep")
@patch("hece.inference.ollama.chat")
def test_ask_retries_once_after_a_server_error(mock_chat, _sleep):
    mock_chat.side_effect = [ServerError("unable to allocate CUDA_Host buffer"), {"message": {"content": "ok"}}]

    assert InferenceEngine().ask("hi") == "ok"
    assert mock_chat.call_count == 2


@patch("hece.inference.time.sleep")
@patch("hece.inference.ollama.chat", side_effect=ServerError("still broken"))
def test_ask_gives_up_after_the_retry(mock_chat, _sleep):
    with pytest.raises(InferenceError, match="still broken"):
        InferenceEngine().ask("hi")
    assert mock_chat.call_count == 2


@patch("hece.inference.ollama.chat", side_effect=ConnectionError("connection refused"))
def test_ask_does_not_retry_when_ollama_is_not_running(mock_chat):
    with pytest.raises(InferenceError):
        InferenceEngine().ask("hi")
    assert mock_chat.call_count == 1
