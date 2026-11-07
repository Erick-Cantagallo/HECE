# HECE: notes for Claude

Code, comments, docs and commit messages stay in English.

## The goal (never lose sight of it)

Generate **creative hypotheses that can be tested and that respect the laws of nature as we know them**. When an idea would break a known law, HECE must neither discard it nor ignore the law: it looks for an alternative path (a new model, assumption, quantity or missing technology) and only then goes beyond the law. Sometimes the honest answer is "current science cannot answer this".

Design rule that follows from it: **the LLM proposes, Python decides.** Nothing the model says may change a score unless Python can verify it (quote present in the text, citation present in the retrieved literature, arithmetic recomputed, dimensions checked). Never present output as validated science; ACTIVE means "passed automated screening", not "true".

## Map

`src/hece/`:
- `main.py`: classic CLI `hece` and `run_hece()` (rejection sampling, up to 4 attempts per requested hypothesis, near misses shown when none pass).
- `discover.py` / `pipeline.py` / `explorer.py`: inventor mode `hece-discover` (explore, recombine, refine, postulate; archive in `runs/*.json`). Details: `docs/DISCOVERY_ENGINE.md`.
- `agents.py`: Expert / Inventor / Critic / Synthesizer; `assess()` scores one hypothesis text.
- `inference.py`: Ollama calls; raises `InferenceError`, retries once on 5xx.
- `verification.py`, `redflags.py`, `numerics.py`, `dimensions.py`, `candidate.py`: deterministic checks. `lawchecks.py`: laws checked by arithmetic (Carnot) become verified violations. Law-level red flags (`redflags.LAW_LEVEL`) block acceptance.
- `benchmark.py` (`hece-benchmark`, cases in `benchmarks/screening.json`): scores fixed texts with a known verdict to measure the screening. Run it after any change to scoring, prompts or red flags; do not tune the filter to the cases without adding held-out ones.
- `simulation.py`: score formula (threshold `MIN_VIABILITY = 0.65`). `conclusion.py`: conclusion without LLM. `paper.py`: PDF.
- `interpreter.py`, `knowledge.py` (+ `tools.py`, arXiv with cache in `.hece_cache/`), `constraints.py`: pipeline front end.
- `hypothesis.py`, `report.py`: legacy, not in the main flow.
- `app.py` (repo root): Streamlit UI.

Architecture: `docs/architecture.md`. History: `CHANGELOG.md`. Plans: `ROADMAP.md`. Real example runs: `examples/`.

## Commands (Windows, Git Bash)

- Tests: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` (about 2 s). After `git pull` or new entry points: `.venv/Scripts/python.exe -m pip install -e ".[dev]"`. Tests must never call Ollama or arXiv: mock `hece.agents.InferenceEngine.ask` and `ScientificToolbox.search_arxiv` (see `tests/conftest.py`).
- Real runs are slow (llama3 8B on a 6 GB GTX 1660 SUPER: ~1.5 to 3.5 min per attempt). Run them with `run_in_background` and `PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8`.
- Ollama: check with `curl -s localhost:11434/api/version`; if down, `ollama list` usually starts the desktop app. Models available: `llama3` (default), `qwen3:4b-instruct-2507-q4_K_M`, `llama3.2:3b`. Choose with `MODEL_NAME`.
- arXiv returns HTTP 429 when called too often; the code degrades gracefully. Use `--no-rag` for quick runs.
- Do not `pip install -e .` while `hece` / `hece-discover` is running: Windows locks the `.exe` and the install half-fails.

## Working rules

- Keep the suite green and add a test for every behaviour change. Match the surrounding style (short docstrings, no comment noise).
- Update `CHANGELOG.md` for user-visible changes. The version lives in `pyproject.toml` and `CITATION.cff`.
- Only claim what a real run or a test showed. Say so when something was not verified with a real model.
- `git push` needs the user's GitHub login (it cannot be done from the agent shell, and `gh` is not installed): give the user the exact command instead.
- `.env`, `reports/`, `runs/`, `.hece_cache/` are git-ignored; `examples/` holds the artifacts that are meant to be published.
