# KMS Governance & Access Control Rules

This document outlines the strict guidelines governing the semantic schema consistency, role-based access control (RBAC), and security audit trails inside the Knowledge Management System (KMS).

---

## 📐 1. Semantic Schema Uniformity
Any metrics registered inside the active metrics tree or stored in `metrics_glossary.json` must strictly support the following schema attributes:
- `id`: A unique snake_case string identifier (e.g. `nim_compression`).
- `name`: A plain English descriptive display name.
- `description`: The conceptual business meaning and significance of the metric.
- `formula`: Executable mathematical syntax utilizing standard terms (e.g., `(interest_income - interest_expense) / average_earning_assets`).
- `trends`: A sequence array of historical integers representing baseline statistics for anomaly detection.

---

## 🔒 2. Role-Based Access Control (RBAC) & Clearance Filters
The system enforces dual boundaries based on User Roles and Security Classifications:
- **User Roles**:
  - **Analyst**: Standard access. Restricted exclusively to **Approved** canonical knowledge nodes. The query retrieval engine must block draft candidates or unapproved items.
  - **SME (Subject Matter Expert)**: Full governance credentials. Allowed to view draft candidates, modify metadata details (domains, tags, relationships), approve items to canonical status, or trigger version rollbacks.
- **Security Clearance Hierarchy**:
  - The security levels are ranked: `Public` < `Internal` < `Confidential` < `Restricted`.
  - The retrieval orchestrator must match the user's `security_clearance` against each node's `security_classification`.
  - Block any chunk where the node's classification level exceeds the user's clearance level.

---

## 📝 3. Security Audit Trails & Governance SLA
- **Auditable Security Traces**:
  - All access, retrieval, and modification events must insert a log entry into the `security_audit_logs` table (detailing `timestamp`, `action`, `user_role`, `knowledge_id`, and `status`).
- **SLA Tracking**:
  - Unapproved candidates created through document ingestion connector synchronization must have a matching entry in the `governance_approvals` SLA table.
  - Track `sme`, `sla_days`, and candidate creation timestamp to enforce governance responsiveness.
