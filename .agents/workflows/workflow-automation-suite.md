---
name: develop-workflow-automation-suite
description: Developer guide for extending the Workflow Automation Suite, modifying DAG validations, and updating active approvals SLA schemas.
trigger: /develop-workflow-automation-suite
---

# Developer Workflow: Developing the Workflow Automation Suite

This guide instructs AI developer agents on how to modify, extend, and test features within the **Workflow Automation Suite** (`AIP/src/workflow_automation/`).

---

## ⚡ 1. Developing Workflow Design & DAG Validation
Workflow validation and cycle checks are coded in `src/workflow_automation/workflow_design/main.py`.
* **Modifying Pipeline Structural Checks**:
  - Locate `validate_pipeline_config(config)`.
  - The validator runs deep-first search (DFS) recursion to verify the configuration contains no cyclic loops.
  - To incorporate new structural guidelines (e.g. enforcing that every pipeline must end with a notification node), add a check rule to the validation loop.
* **Adding JSON Schema Interface Checkers**:
  - To validate that output variables match downstream input formats, extend the schema comparison block in `workflow_design/main.py`.

---

## 🚦 2. Developing Workflow Orchestration & State Handlers
Pipeline execution orchestration and variable mapping reside in `src/workflow_automation/workflow_orchestration/main.py`.
* **Modifying State Coordination Paths**:
  - Locate `run_custom_workflow(config)`.
  - The orchestrator processes steps sequentially. To add new error handlers or recovery strategies (e.g., retrying a step up to 3 times before setting status to `Failed`), modify the retry handler block.
* **Logging Traces to Execution Databases**:
  - Step logs are written to the database through the shared intelligence tracker. To capture new logging metadata (e.g., environment parameters or model IDs), extend the step trace properties array.

---

## 🔑 3. Developing Human-in-the-Loop (HITL) Approvals
Active approvals routing and task resuming are managed inside `src/workflow_automation/task_automation/main.py`.
* **Modifying approvals SLA schemas**:
  - The approvals table `governance_approvals` tracks SLA limits for pending candidates.
  - To update how SLAs are calculated or to alert when an SLA is breached, modify `task_automation/main.py` and register the check triggers in uvicorn boot.

---

## 📊 4. Extending Observability Dashboards
Monitoring telemetries are compiled in `src/workflow_automation/monitoring/main.py`.
* **Adding New Telemetry Metrics**:
  - Locate `run_monitoring_workflow()`.
  - To track a new KPI (e.g., active neo4j transactions count), add a query to the database client in `monitoring/main.py` and format the metric inside the returned JSON payload.
