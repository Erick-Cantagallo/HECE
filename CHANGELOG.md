# Changelog

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