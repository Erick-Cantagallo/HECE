# Changelog

## [Unreleased]
### Added
- Screening benchmark (`hece-benchmark`, cases in `benchmarks/screening.json`): 5 sound hypotheses and 5 that break a known law, scored by the same Critic + Synthesizer + SimulationEngine as `run_hece`. It measures the filter, not the inventor.
- `lawchecks.py`: laws checked by arithmetic. A heat-to-work efficiency above the Carnot limit of the temperatures the text states is a VERIFIED violation of the Second Law (score 0, the calculation is the evidence). In the first benchmark run `llama3` rated such an engine 90%.
- Law-level red flags: energy without any energy input (self-running, "needs no energy"), faster-than-light signalling, energy from the vacuum and entropy reversal now block acceptance and send the hypothesis to human review instead of only costing 15%. Passive devices that need no electricity (solar, radiative cooling) are not flagged.
- New red flags: water memory / structured water, and claims to beat a theoretical or thermodynamic limit (not blocking: changing the assumptions behind a limit is a legitimate creative path).

### Changed
- Accusations that Python cannot verify no longer lower the score (they were -10% each). They are still listed in the report and still require human review. In the first benchmark run this penalty sank 4 of 5 sound hypotheses.
- "unlike" and "as opposed to" count as negations for red flags ("unlike perpetual motion machines, ..." is not a red flag).
- `CLAUDE.md` with the project goal, map, commands and working rules for AI assistants.

### Measured
- `hece-benchmark` with `llama3` 8B: before these changes 1 of 5 sound hypotheses and 0 of 5 law-breaking ones were accepted; after, on a fresh run, 4 of 5 and 0 of 5 (accuracy 0.9). The score alone does not separate the groups (a faster-than-light case and a sound case both scored 60%): the law-level block is what keeps law-breaking ideas out. 10 cases are few, and the red flags were written while looking at them, so new held-out cases are needed before trusting these numbers.

## [1.0.0] - 2026-11-07
### Added
- Inventor mode (discovery engine): explores, recombines and refines mechanisms for a goal, remembers failed attempts, can postulate new physical quantities with SI dimensions, and logs every attempt to `runs/`. Available as `hece-discover`, `python -m hece.discover` and in the Streamlit app (`app.py`, `pip install -e ".[app]"`).
- Verification layer: law accusations, flaws, citations and numbers reported by the agents are checked in Python before they affect the score; red flags and a deterministic conclusion (no LLM).
- Rejection sampling in `run_hece`: only candidates with no verified law violation and at least 65% viability are kept.

### Changed
- Merged the local work with `1.0.0-beta.2`: `InferenceEngine.ask` keeps the optional `temperature` and raises `InferenceError`; the Synthesizer in the refactored orchestrator honours `MAX_RETRIES`.
- Inventor mode stops cleanly when the local model stops answering: the run ends with the reason recorded, the attempts made so far are kept, and no empty PDF is written.
- `.hece_cache/` and `runs/` are git-ignored (generated at runtime).
- When no candidate passes the screening, the classic report shows the best 3 near misses (marked REJECTED, with the reason) instead of an empty "Proposed Hypotheses" section, and the console explains every rejection.
- A server error while Ollama loads the model (seen on a 6 GB GPU: `unable to allocate CUDA_Host buffer`) is retried once instead of ending the run.
- `hece --version` and `hece-discover --version`; `hece.__version__`.
- Documentation updated for 1.0: architecture of both modes, roadmap, Python 3.10+ everywhere.

- Long texts in reports (unverified accusations, rejection reasons, the exploration map) are cut at a word boundary with "..." instead of mid-word.
- `examples/`: two unedited real runs (classic and inventor mode) with their PDFs, console output and exploration log.

### Verified
- Real end-to-end runs with `llama3` (8B) through Ollama on a GTX 1660 SUPER (6 GB) with live arXiv retrieval: classic mode (4 attempts, ~6.5 min) and inventor mode (6 attempts, ~12 min). See `examples/`.
- `qwen3:4b-instruct-2507` runs the classic pipeline end to end (~2 min, fully on the GPU).
- With the Ollama server stopped, `hece` exits with status 1 and a fix-it message, and inventor mode stops cleanly.

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
- Rewritten `README.md` (English, marked as under construction, with the vision in the project's own words and an honest list of what does not exist yet), a banner with an "under construction" label and an architecture diagram.

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