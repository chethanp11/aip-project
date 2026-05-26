---
name: develop-data-science-ml-suite
description: Developer guide for extending the Data Science & ML Suite, modifying dataset profiling validation, and updating Model Pulse drift thresholds.
trigger: /develop-data-science-ml-suite
---

# Developer Workflow: Developing the Data Science & ML Suite

This guide instructs AI developer agents on how to modify, extend, and test features within the **Data Science & ML Suite** (`AIP/src/data_science_ml/`).

---

## 🧼 1. Developing Data Preparation & Profiling
Dataset profiling and validation rules reside in `src/data_science_ml/data_preparation/main.py`.
* **Adding New Profiling Validators**:
  - Locate `run_data_preparation_workflow(columns, dataset)`.
  - To incorporate new data profiling indicators (e.g. tracking duplicate row ratios or skewness thresholds), add validation routines inside the preparation loop.
* **KMS Metric Scheme Matching**:
  - Verify that dataset feature names and types map directly against standard definitions in `metrics_glossary.json`.

---

## 🧪 2. Developing Model Development Experimentation Trackers
Experiment hyperparameter metadata and score tracking are managed inside `src/data_science_ml/model_development/main.py`.
* **Registering Hyperparameter metrics**:
  - Locate `get_model_experiments()`.
  - Experiments track scores like ROC-AUC and F1-score. To introduce a new performance index (e.g. Mean Absolute Percentage Error (MAPE)), extend the metadata dictionary loader.
* **Updating Champion/Challenger Ranks**:
  - To adjust the ranking algorithms that determine champion/challenger classifications, modify the comparison logic inside `model_development/main.py`.

---

## 📝 3. Developing Model Documentation & Compliance Generators
Automated model governance compliance sheets are assembled in `src/data_science_ml/model_documentation/main.py`.
* **Tracing Model Features Lineage**:
  - Locate `run_model_documentation_workflow(model_id, framework, run_id)`.
  - Lineage paths are resolved by querying PostgreSQL and Neo4j relations.
  - To trace new regulatory factors (e.g. Basel 3 liquidity buffers), extend the graph query to include those node mappings.

---

## 💓 4. Developing Model Pulse & Drift Indicators
Live prediction validation and feature stability thresholds are implemented in `src/data_science_ml/model_pulse/main.py`.
* **Adjusting Population Stability Index (PSI) Thresholds**:
  - Locate `run_model_pulse_workflow(metrics)`.
  - The default distribution shift alarm is triggered if calculated feature PSI value $> 0.25$.
  - To make the alert system more sensitive (e.g. warning at PSI $> 0.10$), modify the threshold constants inside `model_pulse/main.py`.
* **Retraining Triggers**:
  - Add logic to invoke task automation capabilities (e.g., dispatching Slack warning alerts or launching active approval DAGs) if drift limits are breached.
