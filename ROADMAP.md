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

## [Planned] Sprint 11: User Interface (UI/UX)
- Option A: Streamlit Web UI for browser-based investigations.
- Option B: Rich CLI Terminal Interface for a cyberpunk laboratory feel.