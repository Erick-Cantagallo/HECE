# Goal Interpreter Specification

**Module:** Goal Interpreter

**Status:** Draft v1.0

**Milestone:** Sprint 1 - Core Architecture

---

# Purpose

The Goal Interpreter is the first reasoning component of HECE.

Its responsibility is to transform a natural language objective into a structured scientific problem that the remaining engines can understand.

It does not generate hypotheses.

It does not evaluate feasibility.

It only understands the user's intention.

---

# Responsibilities

The Goal Interpreter must:

- Interpret the user's objective.
- Detect the scientific domains involved.
- Extract relevant concepts.
- Detect implicit constraints.
- Detect explicit constraints.
- Estimate the complexity of the objective.
- Produce a structured Goal Analysis.

---

# Inputs

The Goal Interpreter receives:

```text
Natural language goal
```

Example:

```text
I want to breathe underwater.
```

---

# Outputs

The module returns a GoalAnalysis object.

Example:

```text
GoalAnalysis

Goal:
"I want to breathe underwater."

Domains:
- Biology
- Chemistry
- Medicine

Keywords:
- breathe
- underwater
- oxygen

Detected Constraints:
- Human lungs
- Gas exchange
- Water pressure

Estimated Complexity:
7/10
```

---

# What this module MUST NOT do

The Goal Interpreter must never:

- Invent scientific explanations.
- Generate hypotheses.
- Judge if something is possible.
- Search scientific papers.
- Simulate experiments.

Those responsibilities belong to other modules.

---

# Internal Pipeline

Natural Language

↓

Intent Detection

↓

Keyword Extraction

↓

Scientific Domain Detection

↓

Constraint Identification

↓

Complexity Estimation

↓

GoalAnalysis

---

# Expected Future Improvements

Future versions may include:

- Multiple language support.
- Ontology-based reasoning.
- Knowledge graph integration.
- LLM-assisted interpretation.
- Domain confidence estimation.

---

# Unit Tests

The following cases should always be tested.

Case 1

Input

```text
I want to breathe underwater.
```

Expected

Domain:

- Biology
- Chemistry

Keywords:

- breathe
- underwater

---

Case 2

Input

```text
Create fire from the human body.
```

Expected

Domain:

- Biology
- Chemistry
- Physics

Keywords:

- fire
- body
- combustion

---

Case 3

Input

```text
Travel faster than light.
```

Expected

Domain:

- Physics

Constraints

- Relativity

---

# Design Principles

The Goal Interpreter must be:

- Deterministic
- Explainable
- Modular
- Replaceable
- Testable
- Independent