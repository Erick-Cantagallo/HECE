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

## [Planned] Sprint 9: Multi-Hypothesis & Scientific Paper Generation
- Refactor the Orchestrator to generate multiple, distinct hypotheses.
- Implement a strict citation requirement, linking generated ideas to RAG (ArXiv) sources.
- Create `paper.py` using `fpdf2` to automatically compile the entire investigation into a formatted PDF Scientific Paper.