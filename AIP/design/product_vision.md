# Product Vision: AIM Intelligence Platform (AIP)

## 1. Platform Identity

AIM Intelligence Platform (AIP) is a banking analytics operating system implemented as a FastAPI application with a static HTML/CSS/JS shell and suite-specific micro-frontends. The product goal is to let analysts perform governed reporting, knowledge-grounded analysis, workflow automation, and model lifecycle review from one authenticated workspace.

The current implementation in `AIP/src/` is intentionally split from infrastructure and data in `AIP-Infra/`:

- `AIP/src/` contains API routes, workflows, capabilities, UI shells, and reusable client code.
- `AIP-Infra/` contains Docker Compose services, PostgreSQL volumes, Neo4j state, Redis state, logs, reports, artifacts, archives, and KMS/LMS seed data.
- Application code should cross this boundary through `src.shared.config` and `src.shared.infra` clients, not direct hardcoded data paths.

## 2. Business Problem

Banking analytics teams need to answer high-value questions while preserving metric consistency, lineage, access controls, and auditability. The implemented AIP runtime addresses these pain points:

| Pain point | Implemented product response |
| --- | --- |
| Report sprawl and duplicate analytical artifacts | PRISM parses report metadata/files, compares SQL and schema overlap, and returns rationalization insights. |
| Manual report creation and review loops | Report Builder manages multi-step HITL report sessions, agent decisions, SME feedback, and published report outputs. |
| Unstructured business questions | Conversational BI combines KMS context, LMS source data, LLM output when available, and deterministic fallbacks. |
| Inconsistent metric interpretation | Shared `metric_interpretation`, KMS glossary, and narrative templates standardize formulas and explanations. |
| Uncontrolled data access | Auth sessions carry role, clearance, allowed domains, and allowed tables used by KMS and Analytics DB flows. |
| Hidden database dependencies | Database Explorer exposes schema catalogs, visual filters, and read-only SQL against `analytics-source-db`. |
| Manual workflow execution | Workflow Automation validates DAGs, runs capability nodes, supports HITL approval pauses, and logs telemetry/lineage. |
| Model governance overhead | DS/ML modules generate preparation summaries, experiment lists, documentation, and drift/model pulse outputs. |

## 3. Users, Roles, and Access Boundaries

AIP uses a centralized login route in `src/main.py` backed by KMS users in PostgreSQL. Login stores a session payload in `shared.session.active_sessions`; middleware places the current token and agent persona into `shared.intelligence.active_agent_context` for every protected request.

### Primary user families

- **Analyst profiles**: use reporting, BI, analytics, automation, model lifecycle, KMS retrieval, and database exploration within allowed domains/tables.
- **SME profiles**: use KMS governance workflows, candidate review, source connector sync, canonical approval, rollback, and KMS administration.
- **Platform/operator profile behavior**: infrastructure and data movement remain outside the application tree under AIP-Infra.

### Implemented profile controls

- Session token prefix: `AIP-...` bearer token required for `/api/v1/*` routes except auth/static bypasses.
- Session payload: `username`, `role`, `clearance`, `display_name`, optional `allowed_domains`, and optional `allowed_tables`.
- KMS retrieval applies role/security filters over canonical knowledge classification and approval status.
- Analytics DB table listing and raw SQL paths inspect active session `allowed_tables` and block unauthorized table access.
- Custom SQL is read-only: only `SELECT` and `WITH` are allowed; DDL/DML keywords are rejected.

## 4. Product Surface

### 4.1 Unified Shell

Implemented in `AIP/src/ui/`.

The shell provides:

- Login tabs for Analyst Console and SME Console.
- Role-specific dropdown user choices.
- Local storage token management (`AIP_API_KEY`, role, display name, username).
- A sidebar for suite navigation.
- Iframe-based micro-frontend embedding.
- Platform telemetry refresh from `/api/v1/capabilities` and `/api/v1/execution-logs`.
- Logout and clear-cache controls.

### 4.2 Knowledge Management System (KMS)

Implemented in `AIP/src/kms/index.py` and `AIP/src/kms/ui/`.

KMS is the semantic grounding core. It creates and uses PostgreSQL tables for:

- `graph_nodes`, `graph_edges`
- `vector_chunks`
- `canonical_knowledge`
- `candidate_knowledge`
- `business_terms`
- `metrics_glossary`
- `analytical_templates`
- `knowledge_articles`
- `security_audit_logs`
- `governance_approvals`
- `observability_metrics`
- `source_connectors`
- `business_domains`
- `kms_users`

Seed data is loaded from `AIP-Infra/storage/kms/seeds`. Graph entities are also synchronized with Neo4j when available. Retrieval uses token overlap over `vector_chunks`, canonical metadata enrichment, Neo4j neighbor traversal, clearance filtering, contradiction checks, missing-context diagnostics, and trace generation.

### 4.3 Analytics Source Database Explorer

Implemented in `AIP/src/db_explorer/ui/` and `AIP/src/shared/infra/analytics_client.py`.

The Database Explorer lets users:

- View table catalog from `analytics-source-db`.
- Inspect table schemas.
- Build visual filter criteria with safe operators.
- Run read-only SQL from a SQL console.
- Export query results as JSON.

This is the primary UX for direct data exploration. It does not bypass access controls; table visibility and query permission checks respect active session restrictions.

## 5. Four Product Suites

### 5.1 Reporting Suite

| Product | Implemented modules | Current behavior |
| --- | --- | --- |
| PRISM | `reporting/prism/main.py`, `/ui/reporting/prism` | Accepts report metadata or uploads (`xlsx`, `xls`, `html`, `csv`), parses schema/query signals, identifies duplicates and overlaps, and summarizes consolidation opportunities. |
| Report Building | `reporting/report_building/main.py`, `/ui/reporting/report_building` | Runs a six-stage HITL workflow: requirements, data transformation, schema, UX layout, final review, publish. Publishes HTML reports to `config.REPORT_PATH` served under `/reports`. |
| Conversational BI | `reporting/conversational_bi/main.py`, `/ui/reporting/conversational_bi` | Answers natural language questions using KMS retrieval, LMS tables, live LLM when configured, and resilient fallback messaging/chart generation. |
| Proactive Insights | `reporting/proactive_insights/main.py`, `/ui/reporting/proactive_insights` | Runs anomaly scans over NIM/NPL trend arrays using the shared metric interpretation capability and emits alert cards. |

### 5.2 Business Analytics Suite

| Product | Implemented modules | Current behavior |
| --- | --- | --- |
| Insight Discovery | `business_analytics/insight_discovery/main.py` | Detects segment volatility and produces surfaced insight cards from segment timelines. |
| Root Cause Analysis | `business_analytics/root_cause_analysis/main.py` | Decomposes metric deltas, ranks factor contribution, and can use prompt-guided LLM summaries when configured. |
| What-if Analysis | `business_analytics/what_if_analysis/main.py` | Simulates rate/asset/NPL changes, calculating interest income, deposit expense, net spread, default cost, and risk-adjusted NIM. |
| Business Narratives | `business_analytics/business_narratives/main.py` | Generates channel-specific business communications with LLM or procedural fallbacks. |

### 5.3 Workflow Automation Suite

| Product | Implemented modules | Current behavior |
| --- | --- | --- |
| Workflow Design | `workflow_automation/workflow_design/main.py` | Validates workflow DAG structure, checks cycles, validates nodes/edges/capabilities, and can register workflow definitions into KMS/Neo4j. |
| Workflow Orchestration | `workflow_automation/workflow_orchestration/main.py` | Topologically executes capability DAGs, resolves dynamic variables, persists workflow state to Redis when available, and supports approval pauses. |
| Task Automation | `workflow_automation/task_automation/main.py` | Runs queued isolated code tasks, tracks task history, manages active approvals, and resumes paused approvals. |
| Monitoring | `workflow_automation/monitoring/main.py` | Initializes monitoring tables, logs orchestrator runs/steps/artifacts, reports telemetry, and provides lineage graph data through Neo4j. |

### 5.4 Data Science and ML Suite

| Product | Implemented modules | Current behavior |
| --- | --- | --- |
| Data Preparation | `data_science_ml/data_preparation/main.py` | Profiles dataset columns/nulls/schema readiness and returns preparation guidance. |
| Model Development | `data_science_ml/model_development/main.py` | Lists model experiment metadata, champion/challenger values, and evaluation indicators. |
| Model Documentation | `data_science_ml/model_documentation/main.py` | Generates model documentation/compliance output using model metadata and optional prompt guidance. |
| Model Pulse | `data_science_ml/model_pulse/main.py` | Evaluates accuracy/latency trends, computes drift indicators/PSI, and returns chart specs and agent dialogue. |

## 6. Shared Capability Vision

AIP treats reusable reasoning blocks as registered capabilities. At startup `src/main.py` registers:

- `knowledge_retrieval`
- `context_management`
- `summarization`
- `narrative_generation`
- `metric_interpretation`
- `visualization`
- `orchestration`
- `mcp_integration`

The product vision is that suite workflows compose these capability contracts instead of duplicating logic. Capabilities remain stateless where possible; state is held in sessions, infrastructure services, workflow stores, or AIP-Infra storage.

## 7. Non-Goals and Guardrails

- AIP is not a generic chatbot. Conversational BI must ground answers in KMS/LMS context or present explicit fallback limitations.
- AIP source code should not embed institutional knowledge/data that belongs under AIP-Infra seeds or databases.
- Product workflows should not open local SQLite files or hardcoded `src/kms/data` paths.
- UI micro-frontends should call `/api/v1/*` with the shell-managed bearer token.
- Custom SQL must remain read-only and permission-filtered.
- Report/artifact/log writes should use configured AIP-Infra paths.
