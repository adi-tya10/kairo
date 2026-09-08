# ADR-003: Deterministic Rule Engines with Grounded LLM Synthesis

> **Status:** Accepted  
> **Date:** 2026-08-26  
> **Deciders:** Principal Software Architect, AI Research Lead  

---

## Context
Deploying an autonomous, unconstrained LLM agent to directly reason over code-versus-ticket state produces hallucinated anomalies, inconsistent state evaluations, and uncontrolled LLM API token expenses. Conversely, pure rule engines cannot generate natural, intuitive executive handoff narratives or answer interactive engineering questions.

## Decision
Separate the reasoning pipeline into two distinct layers:
1. **Deterministic Rule Engine (Python):** State machine evaluations and Hidden-Work rules (`HW-01` to `HW-05`) execute as deterministic Python algorithms with 100% test coverage.
2. **Evidence-Grounded LLM Synthesizer:** LLMs (Google Gemini / Anthropic Claude at $T=0.1$) receive structured assertion payloads and are strictly constrained by JSON schemas and mandatory inline citations (`[Source: Jira-421]`, `[Source: PR #834]`).

## Consequences
* **Positive:** 100% deterministic anomaly detection, predictable compute costs, cryptographic citation integrity, and elimination of ungrounded hallucinations.
* **Trade-off:** Prompt templates and schemas must be strictly versioned in `packages/prompts/` and `packages/schemas/`.
