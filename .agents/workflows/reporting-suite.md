---
name: develop-reporting-suite
description: Developer guide for extending the Reporting Suite code, adding report templates, editing building states, and testing PRISM SQL overlap calculations.
trigger: /develop-reporting-suite
---

# Developer Workflow: Developing the Reporting Suite

This guide instructs AI developer agents on how to modify, extend, and test features within the **Reporting Suite** (`AIP/src/reporting/`).

---

## 🔍 1. Developing PRISM (Report Inventory Intelligence)
PRISM rationalization calculations are implemented inside `AIP/src/reporting/prism/main.py`.
* **Adding SQL Parsing Normalizations**:
  - Locate `run_prism_workflow(reports)`.
  - To add parsing normalizations (e.g. replacing punctuation or isolating joins), modify the keyword set extraction function.
* **Refining Overlap Coefficients**:
  - The SQL token overlap calculation uses a Jaccard index:
    $$\text{Overlap Coefficient} = \frac{|A \cap B|}{|A \cup B|}$$
  - Standard threshold trigger is set to $\ge 0.85$ for consolidation suggestions. To adjust the threshold, modify the comparison conditional parameter in `prism/main.py`.
* **Writing and Running Tests**:
  - Implement unit tests verifying duplicate report detections under `tests/reporting/test_prism.py`. Test reports should have diverse token overlaps to confirm threshold boundaries.

---

## 🏗️ 2. Developing the Report Building Stateful Pipeline
The Report Builder state machine is managed in `src/reporting/report_building/main.py`.
* **Modifying Building Workflow States**:
  - Check the step progression handler `advance_workflow_step(session_id, step, approved, feedback)`.
  - The states advance sequentially ($1 \rightarrow 2 \rightarrow 3 \rightarrow \text{Publish}$).
  - To introduce a new review step (e.g., an automated lint check before SME review), add a step index state check in `report_building/main.py` and implement the corresponding validation logic.
* **Adding New Templates**:
  - Templates reside in `AIP-Infra/storage/kms/seeds/analytical_templates.json`.
  - To register a new layout (e.g. `car_compliance_brief`), insert a JSON record containing `id`, `name`, and the HTML/Markdown `structure` keys, then re-run KMS seeding to ingest the new templates into Postgres.

---

## 💬 3. Developing Conversational BI & Proactive Alerts
- **Conversational BI Routing**:
  - The natural language query routing resides in `src/reporting/conversational_bi/main.py`.
  - It sequentially calls `knowledge_retrieval` (stateless capability) followed by ledger data lookups via `get_lms_table` inside `shared/lms.py`.
  - To support new KPI questions, ensure the metrics are properly added to the `metrics_glossary.json` seeds, and register the SQL-emulated aggregators inside the BI handler.
- **Proactive Anomaly Alerts**:
  - Anomaly monitoring runs Z-score variance logic on metrics histories in `src/reporting/proactive_insights/main.py`.
  - To adjust the sensitivity threshold (default $1.5\sigma$), modify the standard deviation factor parameter in `proactive_insights/main.py`.
