# Changelog

## [1.0.0-beta.2] - 2026-11-05
### Fixed
- `pytest` and `python -m hece.main` failed on a fresh clone with `No module named 'hece'`: the package lives in `src/` but was never installable with its dependencies. `pyproject.toml` now declares them, so `pip install -e .` works, and pytest finds `src/` by itself.
- `requirements.txt` was saved as UTF-16 (PowerShell redirect); it is UTF-8 now, readable by pip, uv, Dependabot and the GitHub UI. Test tooling moved to `requirements-dev.txt`.
- `test_hypothesis.py` only passed with Ollama running and a cooperative model, and `test_knowledge.py` queried the real arXiv API. Both are now fully mocked.
- `MAX_RETRIES` was documented but ignored (the Synthesizer always retried 3 times); it is read from the environment now.
- When Ollama was down or the model was missing, the error text was returned as if it were the model's answer, so the agents reviewed an error message and the run ended with an empty report. `InferenceEngine.ask` now raises `InferenceError` with a message that says how to fix it, and the CLI exits with status 1.
- Version mismatch between `pyproject.toml` (0.1.0), `CITATION.cff` and this changelog.

### Added
- `hece` console command and `python -m hece`. `hece "<goal>" -p <project> -n <count>` runs without prompts; with no arguments the interactive prompts remain.
- GitHub Actions CI (Python 3.10 to 3.13, plus the pinned requirements) and Dependabot.
- Tests for the inference layer, the CLI, `MAX_RETRIES`, the "None trap" filter and an end-to-end pipeline run with the LLM, arXiv and PDF writer mocked (24 new tests, 40 in total).
- Rewritten `README.md` (Portuguese, with an English summary), banner and architecture diagram.

### Changed
- `.env` is no longer tracked: copy `.env.example` to `.env` (git-ignored). After pulling this change, git removes your local `.env`; the defaults are the same, so nothing breaks.
- `requires-python >= 3.10` (required by `arxiv` 4.x).

## [1.0.0-beta] - 2026-07-01
### Added
- Multi-Agent Auto-Retry mechanism for self-healing JSON parsing.
- Deterministic `SimulationEngine` for math-based feasibility scoring without AI hallucinations.
- Dynamic `Synthesizer` conclusion generation in PDF reports.
- Advanced LaTeX and Markdown sanitizers in FPDF2 for graceful math rendering.

### Changed
- Replaced AI numeric guessing with Python deterministic deduction.
- Enforced 500+ word count and ASCII math formatting on LLM Synthesis prompts.
- Refactored `main.py` by abstracting agent orchestration into `agents.py`.

## [0.2.0] - 2026-06-30
### Added
- **Retrieval-Augmented Generation (RAG):** Integrated `arxiv` library into `tools.py` to fetch real-world scientific literature.
- **Dynamic Context:** `KnowledgeEngine` now performs live literature reviews based on user goal keywords.

## [0.1.1] - 2026-06-30
### Added
- **Multi-Agent Orchestration:** Introduced `AgentPool` (`agents.py`) featuring an Expert (proposer), Critic (reviewer), and Synthesizer (formatter) to generate hypotheses.
- **Robust JSON Extraction:** Implemented a regex-style JSON parser in `main.py` to surgically extract data objects and ignore conversational artifacts from local SLMs.

### Changed
- Refactored the core pipeline in `main.py` to bypass the legacy `HypothesisEngine` and utilize the new 3-step agentic workflow.

## [0.1.0] - 2026-06-30
### Added
- **Core Pipeline:** Implemented full deterministic pipeline (GoalInterpreter, KnowledgeEngine, ConstraintEngine, SimulationEngine, ReportGenerator).
- **Inference:** Integrated local LLM (llama3 via Ollama) into the HypothesisEngine.
- **Testing:** Established a full unit test suite with 10 passing tests.
- **Documentation:** Initialized full project documentation (README, Roadmap, Glossary, Security, Code of Conduct, License).
- **Environment:** Configured `.env` support and dependency management.

### Fixed
- Addressed floating-point precision issues in the Simulation Engine.
- Resolved JSON parsing errors in LLM output by tightening strict schema constraints in prompts.