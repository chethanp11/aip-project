---
name: develop-business-analytics-suite
description: Developer guide for extending the Business Analytics Suite, implementing RCA mathematical driver models, and customizing What-if simulations.
trigger: /develop-business-analytics-suite
---

# Developer Workflow: Developing the Business Analytics Suite

This guide instructs AI developer agents on how to modify, extend, and test features within the **Business Analytics Suite** (`AIP/src/business_analytics/`).

---

## 📈 1. Developing Insight Discovery & Exploratory Canvas
Insight Discovery exploratory features reside in `src/business_analytics/insight_discovery/main.py`.
* **Adding Segment Outlier Indicators**:
  - Locate `run_insight_discovery_workflow(segments)`.
  - To incorporate new data dimensions (e.g., branch customer acquisition costs), extend the input segments dictionary parser.
  - Modify the ranking and sorting logic to highlight specific ratio volatility limits.

---

## 🔍 2. Developing Root Cause Analysis (RCA) Drivers
RCA driver deconstructions and formula evaluations are coded in `src/business_analytics/root_cause_analysis/main.py`.
* **Implementing Rate/Volume Formulas**:
  - Standard driver variance calculations partition shifts into Rate and Volume factors:
    $$\Delta \text{Revenue} = (\Delta \text{Volume} \times \text{Rate}_{\text{base}}) + (\Delta \text{Rate} \times \text{Volume}_{\text{base}})$$
  - To edit this math or introduce a mix variance factor, modify the calculations block inside `rca/main.py`.
* **Neo4j Graph Regulatory Dependency Traversals**:
  - The driver graph traversal queries reside inside `rca/main.py` leveraging the `Neo4jClient`.
  - To add new hop relations (e.g., linking loan volume anomalies to Basel capital limits), extend the Cypher match statements inside the query executor.

---

## 🎲 3. Developing the What-If Simulator Sandbox
The scenario projections logic is implemented in `src/business_analytics/what_if_analysis/main.py`.
* **Adding New Projections Parameters**:
  - The standard endpoint `/api/v1/workflows/analytics/what-if` processes four parameters: `loanRate`, `depositRate`, `assets`, and `nplRate`.
  - To add a new parameter (e.g., `liquidityBufferRate`), modify the FastAPI route in `src/main.py` and extend the simulation calculations in `what_if_analysis/main.py` to project downstream net interest spreads.

---

## 📝 4. Extending Business Narratives
Storytelling narrations are constructed in `src/business_analytics/business_narratives/main.py`.
* **Registering Outbound Communication Channels**:
  - Locate `run_business_narratives_workflow(channel, metric, value, growth, driver)`.
  - To add a new communication style (e.g., a formal PDF brief or a Telegram channel format), add a branch to the template formatting conditional and define the message layout rules.
