# PROJECT_CONTEXT

**Project:** HECE — Hypothesis & Creativity Engine

**Current Version:** Pre-Alpha

**Current Milestone:** Sprint 1 — Goal Interpreter

---

# Project Vision

HECE is a scientific investigation platform designed to transform human goals into structured reasoning processes.

Instead of directly answering questions, HECE investigates them.

Its mission is to explore scientific possibilities while remaining transparent about assumptions, evidence, uncertainty, and current scientific limitations.

---

# Core Philosophy

The project follows six fundamental principles.

1. Specification before implementation.

2. Scientific honesty over persuasive answers.

3. Modular architecture.

4. Every reasoning step must be explainable.

5. Deterministic algorithms before AI models.

6. Incremental development.

---

# Current Architecture

User Goal

↓

Goal Interpreter

↓

GoalAnalysis

↓

Knowledge Engine (planned)

↓

Constraint Engine

↓

Hypothesis Engine

↓

Simulation Engine

↓

Scientific Report

↓

PDF Generator

---

# Repository Status

Current Sprint:

Sprint 1 — Goal Interpreter

Completed:

- Repository structure

- Documentation foundation

- Domain language

- Constitution

- GoalInterpreter specification

- GoalAnalysis specification

- Python package configuration

- Initial CLI

- Base models

In Progress:

- Goal Interpreter implementation

Pending:

- Knowledge Engine

- Constraint Engine

- Hypothesis Engine

- Simulation Engine

- Report Generator

---

# Development Rules

Before implementing any important module:

- Define its specification.

- Define its inputs.

- Define its outputs.

- Define its responsibilities.

- Define what it must never do.

Only then should implementation begin.

---

# Coding Standards

- Python 3.12+

- Pydantic models

- Strong typing

- Modular components

- Unit tests

- English for source code

- English for documentation (unless explicitly intended otherwise)

---

# Long-Term Objective

Build a computational platform capable of assisting scientific exploration by decomposing complex objectives into structured investigations and generating transparent, evidence-aware analyses.

---

# Next Immediate Goal

Implement the first functional version of the Goal Interpreter capable of:

- extracting keywords;

- detecting scientific domains;

- estimating complexity;

- identifying initial constraints;

- producing a GoalAnalysis object.

No LLM integration at this stage.

The architecture must be validated before introducing artificial intelligence.

---

# Definition of Success

HECE succeeds when it helps transform difficult or seemingly impossible ideas into structured scientific investigations, allowing humans to understand:

- what is already known;

- what remains unknown;

- what assumptions are being made;

- what discoveries would be required to move forward.