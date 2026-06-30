# HECE - Hypothesis & Creativity Engine

HECE is an open-source computational scientific investigation platform designed to transform human objectives into structured reasoning processes. It decomposes complex scientific problems, identifies constraints, generates hypotheses, and evaluates them deterministically.

## Features
- **Goal Interpreter**: Decomposes natural language scientific goals.
- **Knowledge Engine**: Injects domain-specific axioms and physical laws.
- **Constraint Engine**: Establishes strict logical boundaries.
- **Simulation Engine**: Evaluates hypothesis feasibility against evidence.
- **Local AI Integration**: Supports local LLM inference (via Ollama) to assist reasoning.

## Getting Started
1. Install [Ollama](https://ollama.com).
2. Install dependencies: `pip install -r requirements.txt`.
3. Configure `.env` with your preferred local model.
4. Run: `python -m hece.main`.

## License
MIT License.