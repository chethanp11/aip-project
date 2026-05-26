# Coding Standards & Guidelines

This document establishes the official coding practices and structural conventions for writing Python and FastAPI code in the AIP repository.

---

## 🐍 1. General Python Standards
- **Naming Style**:
  - Class definitions: PascalCase (e.g. `PostgresConnectionWrapper`).
  - Function, variable, and file names: snake_case (e.g. `advanced_retrieval_orchestration`).
  - Constants: UPPER_SNAKE_CASE (e.g. `AIP_DEV_TOKEN`).
- **Module Imports**:
  - Keep absolute path imports based on workspace root (`AIP/`).
  - Avoid cyclic dependencies. Shared logic must live under `src/shared` and be shared by all suites.
- **Comments and Documentation**:
  - Maintain all existing docstrings and inline comments.
  - Document all inputs/outputs using python type hinting or Pydantic validation models.

---

## 🚀 2. FastAPI Endpoint Guidelines
- **Route Definitions**:
  - Keep endpoints clearly structured under `/api/v1/...` routes.
  - Group workflows under their respective product suite prefixes:
    - `/api/v1/workflows/reporting/...`
    - `/api/v1/workflows/analytics/...`
    - `/api/v1/workflows/automation/...`
    - `/api/v1/workflows/ds/...`
- **Response Schemas**:
  - Return structured JSON payloads containing clear status parameters (e.g. `{'success': True, 'output': ...}`).
  - Include appropriate latency metrics and diagnostic logs where useful (e.g., `latencyMs`, `auditTraces`).

---

## 🔒 3. Thread-Safe Request-Scope Telemetry
- All routes must respect the `context_and_auth_middleware` context propagation.
- If writing new routes or background threads that trigger execution tasks, fetch and pass context explicitly:
  ```python
  from shared.intelligence import active_agent_context
  
  # Retrieve current thread-safe request context details
  ctx = active_agent_context.get()
  agent_name = ctx.get('agent', 'Unknown Agent')
  ```

---

## 🛠️ 4. Refactoring & Code Quality
- **Minimal Safe Changes**: Modify only what is requested. Unrelated refactoring or rewrites are highly discouraged.
- **Stateless Capability Invocations**: Do not replicate capability code in workflows. Call them using `invoke_capability(name, inputs)` to ensure a clean, decoupled execution trace.
