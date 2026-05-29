# UX Flows: AIP Analyst Operating System

This document describes the implemented user flows in `AIP/src/ui`, suite micro-frontends, and `/api/v1` routes.

## 1. Shell Authentication Flow

### Entry

User opens `/`. The root shell in `AIP/src/ui/index.html` shows the login screen until a valid token exists in local storage.

### Login steps

1. User chooses **Analyst Console** or **SME Console**.
2. User selects a profile from the dropdown.
   - Analyst options include Treasury, Compliance, Model, and Credit analyst profiles.
   - SME options include Treasury, Compliance, Model, and Credit SME profiles.
3. User enters password.
4. UI posts to `POST /api/v1/auth/login`.
5. API authenticates against KMS `kms_users`.
6. API stores active session payload with role, clearance, allowed domains, and allowed tables.
7. UI stores:
   - `AIP_API_KEY`
   - `AIP_USER_ROLE`
   - `AIP_USER_NAME`
   - `AIP_USER_UNAME`
8. Shell unlocks the main workspace and refreshes telemetry.

### Logout and reset

- **Logout Profile** calls `POST /api/v1/auth/logout`, clears local session fields, and returns to login.
- **Clear Cache** calls logout, clears local/session storage and cookies, then reloads.

## 2. Shell Navigation Flow

After login, the sidebar drives page switching in `AIP/src/ui/index.js`.

Primary pages:

- Dashboard Home
- Reporting Suite
- Business Analytics
- Workflow Automation
- Data Science & ML
- KMS Workspace
- Database Explorer

Each suite page embeds a micro-frontend in an iframe. All same-origin iframes use local storage bearer token forwarding through either a global fetch interceptor or explicit `authedFetch` wrappers. Micro-frontends call APIs through relative `/api/v1` paths so authentication stays bound to the active host and port.

## 3. KMS Workspace Flow

The KMS UI under `/ui/kms` supports search, governance, source connectors, candidates, and context package export.

### Advanced retrieval

1. User enters query and filter values.
2. UI calls `POST /api/v1/kms/query-advanced`.
3. API invokes `advanced_retrieval_orchestration`.
4. UI renders:
   - grounded context
   - matched chunks
   - matched graph/canonical nodes
   - agent traces
   - contradictions
   - missing context diagnostics
   - latency

### Context package export

1. User initiates export/download.
2. UI calls `POST /api/v1/kms/retriever/download`.
3. API runs retrieval, generates package metadata, writes zip entries in memory, and returns an application zip response.
4. Browser downloads `context_pack_*.zip`.

### Candidate governance

1. UI loads candidates from `GET /api/v1/kms/candidates`.
2. SME edits metadata via `POST /api/v1/kms/candidates/edit`.
3. SME takes action through `POST /api/v1/kms/candidates/action`.
4. Approved candidates are promoted into canonical knowledge and synchronized to graph structures where available.

### Source connectors

1. UI lists connectors via `GET /api/v1/kms/connectors`.
2. SME creates connector via `POST /api/v1/kms/connectors`.
3. SME triggers sync via `POST /api/v1/kms/connectors/sync`.
4. API stages simulated source content, updates connector history, and creates candidate knowledge for review.

## 4. Database Explorer Flow

The Database Explorer under `/ui/db_explorer` is the direct data access UX for `analytics-source-db`.

### Table catalog

1. On load, UI calls `GET /api/v1/analytics-data/tables`.
2. `AnalyticsClient.list_tables` returns only tables allowed by the active session.
3. UI renders the table list and connection status.

### Schema inspection

1. User selects a table.
2. UI calls `GET /api/v1/analytics-data/tables/{table_name}/schema`.
3. UI renders schema pills and enables query controls.

### Visual query builder

1. User adds filter rows.
2. Filters include column, operator, and value.
3. UI posts mode `visual` to `POST /api/v1/analytics-data/query`.
4. `AnalyticsClient.query_table` validates table/columns, parameterizes filters, applies limit, and returns records.
5. UI renders a grid and enables JSON export.

### SQL console

1. User writes SQL.
2. UI posts mode `sql` with `sqlQuery`.
3. Server permits only `SELECT` or `WITH` statements.
4. Server blocks DDL/DML keywords.
5. Server rejects unauthorized table references.
6. UI renders returned records or displays a security/error message.

## 5. Reporting Suite Flows

### PRISM

Route group:

- `POST /api/v1/workflows/reporting/prism-lite`
- `POST /api/v1/workflows/reporting/prism/upload`

Flow:

1. User provides report metadata or uploads Excel/HTML/CSV files.
2. API parses report definitions.
3. Workflow normalizes SQL/schema terms.
4. Workflow detects exact duplicate queries, identical schemas, and overlap similarity.
5. UI receives duplicate/overlap lists, usage insights, and consolidation plans.

### Report Builder

Route group:

- `POST /api/v1/workflows/reporting/build/initiate`
- `POST /api/v1/workflows/reporting/build/step`
- `GET /api/v1/workflows/reporting/build/reports`

Flow:

1. Analyst starts create/update mode with requirements and optional context.
2. Workflow creates an in-memory session.
3. User approves each step or rejects with feedback.
4. On approval, specialized agent decisions are generated for that step.
5. Data transformation queries use LMS compatibility access.
6. Final step publishes HTML to `REPORT_PATH`.
7. Published reports are served under `/reports` and listed by route.

### Conversational BI

Route: `POST /api/v1/workflows/reporting/conversational-bi`

Flow:

1. User sends a natural language question.
2. Workflow safely invokes `knowledge_retrieval`.
3. Workflow reads LMS tables when infrastructure is available.
4. Workflow attempts live LLM answer through `call_llm`.
5. If LLM/infra is unavailable, route returns explicit fallback narrative instead of failing.
6. Workflow returns narrative and optional Vega-Lite chart spec.

### Proactive Alerts

Route: `GET /api/v1/workflows/reporting/proactive-insights`

Flow:

1. UI requests alert feed.
2. Workflow evaluates NIM and NPL trends through `metric_interpretation`.
3. Workflow returns alert cards with severity, message, and recommendation.

## 6. Business Analytics Flows

### Insight Discovery

1. UI posts segment timeline data to `/api/v1/workflows/analytics/insight-discovery`.
2. Workflow calculates segment volatility/outlier behavior.
3. UI displays surfaced insights.

### Root Cause Analysis

1. UI posts dataset name, metrics data, and optional prompt to `/api/v1/workflows/analytics/rca`.
2. Workflow ranks contributors and generates RCA explanation.
3. UI displays factor contribution and diagnostic narrative.

### What-if Analysis

1. User adjusts loan rate, deposit rate, assets, and NPL rate.
2. UI posts values to `/api/v1/workflows/analytics/what-if`.
3. Workflow returns projected income, expense, default cost, spread, and risk-adjusted NIM.

### Business Narratives

1. User selects channel and metric context.
2. UI posts to `/api/v1/workflows/analytics/business-narratives`.
3. Workflow returns a channel-targeted narrative with LLM or deterministic fallback text.

## 7. Workflow Automation Flows

### Workflow Design and Execution

1. User builds a DAG in the workflow UI.
2. UI posts DAG config to `POST /api/v1/workflows/automation/run`.
3. API validates structure with `validate_pipeline_config`.
4. Workflow Orchestrator topologically executes capability nodes.
5. Dynamic variables are resolved from previous node outputs.
6. Nodes requiring approval pause and create approval records.
7. Completed run returns traces, node statuses, and outputs.

### Approval handling

- `GET /api/v1/workflows/automation/approvals` lists paused approvals.
- `POST /api/v1/workflows/automation/approve` resumes or aborts the approval path.

### Task automation

- `POST /api/v1/workflows/automation/tasks/submit` queues code task execution.
- `GET /api/v1/workflows/automation/tasks/history` returns task history.

### Monitoring and lineage

- `GET /api/v1/workflows/automation/telemetry` returns run/step telemetry.
- `GET /api/v1/workflows/automation/monitoring/lineage` returns Neo4j workflow lineage when graph infrastructure is available.

## 8. Data Science and ML Flows

### Data Preparation

1. User submits columns and dataset preview to `/api/v1/workflows/ds/prep`.
2. Workflow returns profiling and readiness notes.

### Model Development

1. UI calls `GET /api/v1/workflows/ds/experiments`.
2. Workflow returns experiment metadata and champion/challenger comparisons.

### Model Documentation

1. User submits model id, framework, champion run, and prompt.
2. Workflow returns governance/compliance documentation output.

### Model Pulse

1. User submits accuracy/latency metrics.
2. Workflow computes drift score, PSI-style output, latency summary, agent dialogue, and Vega-Lite spec.
3. UI renders drift state and performance chart.

## 9. Error Handling UX

Implemented UX patterns:

- API auth failures clear the local token and return to login.
- Database Explorer displays connection offline state when analytics DB is unavailable.
- Conversational BI returns fallback narrative when optional KMS/LMS/LLM dependencies are unavailable.
- KMS query outputs missing-context and contradiction warnings instead of silently hiding retrieval gaps.
- Workflow validation returns structural errors before orchestration starts.
- SQL Console surfaces permission errors for non-read-only or unauthorized table queries.

## 10. UX Guardrails

- UI routes must call relative `/api/v1/*` paths and pass the current `AIP_API_KEY` bearer token.
- Micro-frontends should not embed hardcoded secrets or direct database credentials.
- User-facing copy should distinguish infrastructure errors from analytical results.
- Data exploration is read-only from the UI.
- KMS governance actions require authenticated sessions and should preserve candidate/canonical auditability.
