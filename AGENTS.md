# AGENTS.md

# Purpose

This repository uses an AI-assisted engineering workflow.

Every prompt is treated as a software engineering requirement:
- feature
- enhancement
- refactor
- bug fix
- architectural change
- debugging request
- test failure
- operational issue
- documentation update

The responsibility of the agent is to:
1. understand the requirement
2. analyze impact
3. preserve architectural consistency
4. update implementation
5. update validation/tests
6. execute verification
7. return concise outcome summaries

The goal is disciplined software engineering, not autonomous experimentation.

---

# Context Loading

Before making changes:

1. Read:
   - `.agents/project-context.md`

2. Dynamically retrieve relevant context from:
   - `.agents/skills/`
   - `.agents/agents/`
   - `.agents/memory/`

3. Retrieve only context relevant to the current task.

Do not load unnecessary files or unrelated context.

The system should remain lightweight, adaptive, and context-driven.

---

# Repository Authority Model

The repository follows strict authority boundaries.

## design/

Contains:
- architecture
- workflows
- system behavior
- contracts
- domain models
- operational expectations

Rules:
- Update design documentation when behavior or architecture changes.
- Preserve consistency between implementation and design.
- Avoid undocumented architectural drift.

Always update design/ when src/ is updated
---

## src/

Contains:
- application implementation
- APIs
- orchestration
- domain logic
- services
- frontend
- backend
- infrastructure integration

Rules:
- Prefer minimal high-confidence modifications.
- Preserve module boundaries.
- Avoid unnecessary abstractions.
- Avoid speculative implementation.

---

## tests/

Contains:
- unit tests
- integration tests
- regression tests
- end-to-end tests
- fixtures

Rules:
- Behavior changes require test coverage.
- Bug fixes require regression tests when appropriate.
- Tests must validate actual behavior, not implementation trivia.
- Prefer deterministic tests.

---

# Engineering Principles

## Preserve Architectural Integrity

Do not introduce:
- duplicate sources of truth
- hidden side effects
- bypass paths
- tightly coupled modules
- implicit behavior
- uncontrolled global state

Prefer:
- explicit contracts
- deterministic workflows
- traceable execution
- bounded responsibilities
- maintainable structures

---

## Prefer Simplicity

Prefer:
- simple solutions
- readable code
- maintainable structures
- explicit flows

Avoid:
- framework overengineering
- premature optimization
- speculative abstractions
- unnecessary orchestration layers
- unnecessary indirection

---

## Prefer Minimal Safe Changes

For fixes and enhancements:
- modify the smallest reasonable surface area
- preserve existing behavior unless intentionally changing it
- avoid unrelated refactors
- avoid broad rewrites without clear justification

---

## Keep Behavior Deterministic

Avoid:
- nondeterministic outputs
- unstable ordering
- hidden runtime mutations
- unpredictable side effects

Systems should remain:
- inspectable
- testable
- reproducible
- auditable

---

# Skills

`.agents/skills/` contains reusable execution knowledge.

Examples:
- API patterns
- testing patterns
- migration patterns
- debugging workflows
- frontend patterns
- parsing logic
- orchestration patterns

Rules:
- Dynamically retrieve relevant skills.
- Reuse existing patterns before inventing new approaches.
- Do not rigidly force skill usage.
- Use judgment based on the current requirement.

---

# Agents

`.agents/agents/` contains specialized engineering viewpoints.

Examples:
- backend engineer
- frontend engineer
- reviewer
- debugger
- architect
- performance optimizer

Rules:
- Use agents only when useful for the task.
- Agents represent capability specialization, not personalities.
- Do not simulate roleplay behavior.
- Keep engineering decisions grounded and practical.

---

# Memory

`.agents/memory/` contains reusable repository knowledge.

Examples:
- conventions
- architectural decisions
- recurring implementation patterns
- operational lessons
- known pitfalls

Rules:
- Reuse prior repository knowledge where relevant.
- Preserve consistency with prior decisions unless intentionally changing direction.
- Avoid repeating solved mistakes.

---

# Design Consistency Rules

When making changes:
- preserve naming consistency
- preserve API contract consistency
- preserve folder responsibility boundaries
- preserve configuration conventions
- preserve architectural direction

If implementation conflicts with design:
1. reconcile the conflict
2. update design if required
3. keep implementation and documentation aligned

---

# Testing Expectations

Relevant validation should be executed whenever possible.

Examples:
- unit tests
- integration tests
- linting
- type checks
- build validation
- smoke tests

Do not claim success without validation.

If validation cannot be executed:
- clearly explain why
- identify remaining uncertainty

---

# Response Expectations

After completing work, provide concise summaries including:

1. What changed
2. Design updates
3. Implementation updates
4. Tests added or updated
5. Validation executed
6. Remaining issues or risks

Avoid unnecessary verbosity.

---

# Operational Philosophy

This repository is optimized for:
- execution speed
- maintainability
- architectural consistency
- deterministic engineering
- AI-assisted development

The objective is not autonomous coding.

The objective is high-quality software engineering accelerated through structured AI assistance.

---

# Final Rule

Do not introduce unnecessary complexity.

Prefer:
- clarity
- correctness
- maintainability
- explicit behavior
- disciplined execution

The best solution is usually the simplest solution that preserves long-term architectural integrity.