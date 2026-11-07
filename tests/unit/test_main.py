# HECE/tests/unit/test_main.py
from unittest.mock import patch

from hece.inference import InferenceError
from hece.main import main


@patch("hece.main.run_hece")
def test_one_shot_mode_runs_without_prompts(mock_run):
    assert main(["How does X work?", "--project", "Orion", "-n", "3"]) == 0
    mock_run.assert_called_once_with("Orion", "How does X work?", 3)


@patch("hece.main.run_hece")
def test_one_shot_mode_uses_defaults(mock_run):
    assert main(["How does X work?"]) == 0
    mock_run.assert_called_once_with("Investigation", "How does X work?", 2)


@patch("hece.main.run_hece")
def test_hypothesis_count_never_drops_below_one(mock_run):
    main(["goal", "-n", "0"])
    mock_run.assert_called_once_with("Investigation", "goal", 1)


@patch("hece.main.run_hece")
def test_interactive_mode_asks_for_everything(mock_run):
    with patch("builtins.input", side_effect=["Orion", "A goal", "4"]):
        assert main([]) == 0
    mock_run.assert_called_once_with("Orion", "A goal", 4)


@patch("hece.main.run_hece")
def test_interactive_mode_falls_back_on_an_invalid_count(mock_run):
    with patch("builtins.input", side_effect=["Orion", "A goal", "many"]):
        assert main([]) == 0
    mock_run.assert_called_once_with("Orion", "A goal", 2)


@patch("hece.main.run_hece")
def test_empty_goal_is_rejected(mock_run, capsys):
    with patch("builtins.input", side_effect=["Orion", "   ", "2"]):
        assert main([]) == 1
    mock_run.assert_not_called()
    assert "cannot be empty" in capsys.readouterr().err


@patch("hece.main.run_hece")
def test_closed_stdin_aborts_cleanly(mock_run):
    with patch("builtins.input", side_effect=EOFError):
        assert main([]) == 1
    mock_run.assert_not_called()


@patch("hece.main.run_hece", side_effect=InferenceError("Could not reach Ollama."))
def test_llm_outage_is_reported_without_a_traceback(_run, capsys):
    assert main(["goal"]) == 1
    assert "Could not reach Ollama." in capsys.readouterr().err
