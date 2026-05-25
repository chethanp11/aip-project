---
name: AIP KMS Grounder
description: Rules for validating metric trees, glossary terms, and analytical playbooks inside the KMS.
---

# Skill: AIP KMS Grounder

## 📌 Context
The **Knowledge Management System (KMS)** acts as the semantic foundation of AIP, storing all structured metric formulas, playbooks, and definitions in `/knowledge/`. This skill outlines how to maintain these version-controlled configuration assets.

---

## 📐 Grounding & Seeding Guidelines

### 1. Data Schema Uniformity
Any metric entry in `knowledge/metrics_glossary.json` must support:
*   `id`: Unique snake_case string identifier.
*   `name`: Plain English display name.
*   `description`: Conceptual business meaning.
*   `formula`: Executable mathematical syntax (e.g. `cogs / gross_revenue`).
*   `trends`: Sequence array of historical integers representing baseline statistics.

### 2. Hallucination Safeguard Policies
To prevent AI model calculations hallucinating:
*   Before generating narratives, invoke `knowledge_retrieval` to download the specific metric details.
*   All computed stats (anomalies, percentage variances) must be formatted directly against matching template keys defined in `knowledge/analytical_templates.json`.
*   If a user asks about an unknown term, refuse to guess and return: *"Metric not found in KMS. Grounded default metrics: Gross Revenue, CAC, COGS."*

### 3. Report Rationalization (PRISM) rules
*   Duplicates matching must clean and normalise SQL statement whitespaces and cases before matching queries.
*   Overlap coefficients calculations must map sets of token overlaps (Jaccard Index) to determine merge recommendations:
    $$\text{Overlap Coefficient} = \frac{|A \cap B|}{|A \cup B|}$$
