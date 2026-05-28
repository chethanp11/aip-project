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
The system enforces boundaries based on User Roles, Specialized Analyst Profiles, and Security Classifications:
- **User Roles & Profiles**:
  - **Analyst**: Restricted exclusively to **Approved** canonical knowledge nodes. Standard analysts can access all domains.
  - **Specialized Analyst Profiles**:
    - **Treasury Analyst**: Access restricted to `Treasury & Capital Management, Cash Management` domains.
    - **Compliance Analyst**: Access restricted to `Regulatory Compliance` domains.
    - **Model Analyst**: Access restricted to `Model Risk Management (MRM)` domains.
    - **Credit Analyst**: Access restricted to `Credit Portfolio Risk` domains.
  - **SME (Subject Matter Expert)**: Full governance credentials. Allowed to view draft candidates, modify metadata details (domains, tags, relationships), approve items to canonical status, or trigger version rollbacks.
- **Dynamic Context Grounding Filters**:
  - When querying the KMS, the retrieval orchestrator extracts `allowed_domains` from the active analyst profile context.
  - Nodes and chunks matching unauthorized domains are dynamically filtered out.
- **Security Clearance Hierarchy**:
  - The security levels are ranked: `Public` < `Internal` < `Confidential` < `Restricted`.
  - The retrieval orchestrator matches the user's `security_clearance` against each node's `security_classification`.
  - Block any chunk where the node's classification level exceeds the user's clearance level.

---

## 📝 3. Security Audit Trails & Governance SLA
- **Auditable Security Traces**:
  - All access, retrieval, and modification events must insert a log entry into the `security_audit_logs` table (detailing `timestamp`, `action`, `user_role`, `knowledge_id`, and `status`).
- **SLA Tracking**:
  - Unapproved candidates created through document ingestion connector synchronization must have a matching entry in the `governance_approvals` SLA table.
  - Track `sme`, `sla_days`, and candidate creation timestamp to enforce governance responsiveness.
