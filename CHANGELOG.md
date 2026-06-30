# Changelog

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