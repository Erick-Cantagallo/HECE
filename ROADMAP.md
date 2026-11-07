# Roadmap

## [Done] Sprint 1: Goal Interpreter
- Foundation, base models, CLI.

## [Done] Sprint 3-5: Engine Core
- Knowledge, Constraint, Hypothesis, and Simulation engines implemented.

## [Done] Sprint 7: Agentic Orchestration
- Implemented `AgentPool` with specialized roles (Expert, Critic, Synthesizer).
- Replaced linear mock hypothesis generation with a multi-agent consensus workflow.
- Added a robust JSON extraction layer to handle conversational filler from local LLMs.

## [Done] Sprint 8: External Integration (RAG)
- Created `ScientificToolbox` using the `arxiv` API.
- Upgraded `KnowledgeEngine` to autonomously search and inject real-world paper summaries into the AI's context.

## [Done] Sprint 9: Multi-Hypothesis & Scientific Paper Generation
- Refactored the Orchestrator to generate multiple, distinct hypotheses.
- Implemented a strict citation requirement, linking generated ideas to RAG (ArXiv) sources.
- Created `paper.py` using `fpdf2` to automatically compile the entire investigation into a formatted PDF Scientific Paper.

## [Done] Sprint 10: Deterministic Math & Credibility
- Replaced AI numeric guessing with Python deterministic deduction to prevent "innumeracy" flaws.
- Documented calculation methodology explicitly in the final PDF.
- Enforced deep paragraph generation and plain-text math rendering, along with LaTeX sanitization in FPDF2.

## [Done] Sprint 11: Verification & User Interface
- Python checks every claim that affects a score: law accusations need a real quote, invented citations are dropped, unit conversions are recomputed and known pseudo-science patterns are flagged.
- Rejection sampling in the classic pipeline and a deterministic conclusion (no LLM).
- Streamlit web interface (`streamlit run app.py`) for both modes.

## [Done] Sprint 12: Inventor Mode (v1.0)
- Discovery engine: explore, recombine, refine and postulate strategies, with an archive of every attempt and the reason it failed.
- Postulated quantities must declare SI dimensions, an equation, a magnitude and when they reduce to known physics.
- Real end-to-end runs with a local model; installable package with `hece` and `hece-discover` commands; CI on Python 3.10 to 3.13.

## [Done] Sprint 13: Calibration & Alternative Paths
- Screening benchmark with held-out cases (`benchmarks/RESULTS.md`); default model chosen by measurement.
- Carnot check in Python; law-level red flags block acceptance.
- REROUTE: an idea that runs into a law gets an alternative-path attempt; reports list what would have to be invented first.

## [Planned] Next
- A new held-out set, then more arithmetic law checks (Betz limit, refrigeration COP, Landauer limit, catalysts cannot shift equilibrium), measured on that set.
- Better arXiv queries: the keywords come from the goal's words (e.g. "store"), so the right concept ("specific energy") is often missing.
- Make the judge less harsh on sound ideas without letting violations through (assumption penalty, prompt), measured with the benchmark.
- Built-in laws for more domains (chemistry, materials, medicine).
- Unicode font in the PDF.
