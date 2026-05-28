# System Design Document: AIP Enterprise Architecture

## 1. Implemented Architecture Overview

AIP is implemented as a Python FastAPI gateway plus static micro-frontends. The source-of-truth runtime is `AIP/src/`; infrastructure and data surfaces live in `AIP-Infra/`.

```text
AIP/src/main.py
  ├─ registers shared capabilities
  ├─ installs auth/context middleware
  ├─ exposes /api/v1 routes
  ├─ mounts /reports from AIP-Infra storage
  └─ mounts static micro-frontends under /ui/*

AIP/src/shared/
  ├─ config/            centralized env and AIP-Infra path mapping
  ├─ infra/             Postgres, Analytics, Neo4j, Redis, Storage, Retrieval clients
  ├─ capabilities/      stateless reusable intelligence functions
  ├─ intelligence.py    capability registry, LLM wrapper, contextvars audit logging
  ├─ lms.py             LMS table bootstrap and compatibility query wrapper
  └─ session.py         in-memory active token/session state

AIP/src/kms/
  ├─ index.py           KMS schema, retrieval, governance, sync, packaging
  └─ ui/                KMS governance/retrieval frontend

AIP/src/<suite>/
  ├─ */main.py          stateful workflow implementation
  └─ */ui/              static micro-frontend
```

## 2. Infrastructure Boundary

AIP uses AIP-Infra through configuration and client abstractions only.

| Infra surface | Path/service | Accessing code |
| --- | --- | --- |
| Analytics PostgreSQL | `analytics-source-db`, port `5433` | `PostgresClient`, `AnalyticsClient`, `lms.py` |
| pgvector/platform PostgreSQL | `aip-postgres`, port `5432` when configured | `PostgresClient`, KMS metadata/vector tables |
| Neo4j | `aip-neo4j`, port `7687` | `Neo4jClient`, KMS graph sync, monitoring lineage |
| Redis | `aip-redis`, port `6379` | `RedisClient`, workflow state persistence |
| Reports | `AIP-Infra/storage/reports` | Report Builder, FastAPI `/reports` static mount |
| Artifacts/archives | `AIP-Infra/storage/{artifacts,archives}` | `StorageClient`, workflow/report outputs |
| KMS seeds | `AIP-Infra/storage/kms/seeds` | `load_kms_seed_file`, KMS bootstrap |
| KMS runtime | `AIP-Infra/storage/kms/runtime` | KMS ingestion staging/runtime directories |
| LMS seeds | `AIP-Infra/storage/lms/seeds` | `shared.lms._load_lms_seed` |
| Logs | `AIP-Infra/logs` | KMS ingestion logging and infra checks |

Configuration is centralized in `AIP/src/shared/config/config.py`. It loads `.env`, sets database credentials, sets storage paths, and creates expected directories.

## 3. FastAPI Gateway

The gateway in `src/main.py` provides:

- `NoCacheStaticFiles` to serve static files without stale browser cache.
- CORS middleware for local UI/API calls.
- Auth middleware for `/api/v1/*` routes.
- Agent persona mapping based on request path.
- `active_agent_context` propagation to downstream capabilities.
- API routes for auth, KMS, analytics data, LMS, capabilities, logs, product workflows, task automation, monitoring, and model lifecycle.
- Static UI mounting under `/ui/*` and root shell mounting at `/`.

### Auth bypasses

The middleware bypasses authentication for:

- `OPTIONS`
- root/static UI files
- `/api/v1/auth/login`
- `/api/v1/auth/sme-login`
- non-API static paths

All other `/api/v1/*` requests require a bearer token starting with `AIP-`.

### Request context

After auth, middleware sets:

```python
active_agent_context = {'agent': agent_name, 'api_key': api_key}
```

Capability execution uses that context to log the active agent, mask the token, and attach execution traces.

## 4. Auth and Session Model

### Login

`POST /api/v1/auth/login` calls `authenticate_kms_user` and accepts any registered KMS user. `POST /api/v1/auth/sme-login` delegates to the same login function for backward compatibility.

Successful login creates a token:

```text
AIP-{ROLE}-SESSION-{RANDOM_SUFFIX}
```

The active session is stored in memory with:

- `username`
- `role`
- `clearance`
- `display_name`
- optional `allowed_domains`
- optional `allowed_tables`

### Logout

`POST /api/v1/auth/logout` removes the bearer token from `active_sessions`.

### Security constraints

- KMS auth is backed by the `kms_users` PostgreSQL table.
- Password comparison uses `hmac.compare_digest`.
- Analytics table catalog and SQL execution use active session `allowed_tables`.
- KMS retrieval filters canonical knowledge by status/security classification and active role/clearance.

## 5. Shared Infrastructure Clients

### PostgresClient

`AIP/src/shared/infra/postgres_client.py`

- Opens connections with configured `POSTGRES_*` values.
- Returns `RealDictCursor` dictionaries.
- Converts `?` placeholders to `%s` to keep legacy SQLite-style call sites working.
- Provides single-query and batch execution helpers.

### AnalyticsClient

`AIP/src/shared/infra/analytics_client.py`

- Lists public schema tables.
- Filters table catalog by active session `allowed_tables`.
- Retrieves table schemas.
- Builds safe parameterized visual queries.
- Runs custom read-only SQL with DDL/DML keyword blocking.
- Parses referenced table names and rejects unauthorized table access.

### Neo4jClient

`AIP/src/shared/infra/neo4j_client.py`

- Creates Neo4j Bolt driver.
- Verifies connectivity.
- Executes Cypher queries and returns list-of-dict records.
- Used by KMS graph sync and monitoring lineage.

### RedisClient

`AIP/src/shared/infra/redis_client.py`

- Provides a Redis connection pool.
- Used by orchestration state persistence when Redis is available.

### RetrievalClient

`AIP/src/shared/infra/retrieval_client.py`

- Keeps agent/capability consumers decoupled from KMS internals.
- Delegates search to `advanced_retrieval_orchestration`.

### StorageClient

`AIP/src/shared/infra/storage_client.py`

- Ensures report, artifact, archive, and log directories exist.
- Writes generated content to configured AIP-Infra directories.

## 6. KMS Data Model and Retrieval

KMS is implemented in `AIP/src/kms/index.py`.

### Bootstrap sequence

On first KMS database access:

1. Open PostgreSQL connection through `PostgresClient`.
2. Create graph, vector, canonical, candidate, governance, audit, connector, glossary, domain, user, and observability tables.
3. Seed KMS glossary/template/article/domain records from `KMS_SEED_PATH`.
4. Seed graph/canonical/candidate/source connector baseline from `knowledge_seed.json` when baseline nodes are absent.
5. Sync graph nodes/edges to Neo4j when available.
6. Verify Neo4j connectivity without blocking KMS if Neo4j is unavailable.

### Retrieval sequence

`advanced_retrieval_orchestration` performs:

1. Tokenization of analyst query.
2. Vector chunk scoring using token overlap.
3. Canonical metadata enrichment.
4. Analyst/SME approval and clearance filtering.
5. Optional domain/source/type/SME/tag/freshness filters.
6. Graph neighbor traversal through `graph_edges`/Neo4j-compatible wrappers.
7. Contradiction and missing-context diagnostics.
8. Trace generation with latency metrics.
9. Security audit log write.

### Governance sequence

- `ingest_custom_file_to_kms` creates candidate knowledge from uploaded text.
- `sync_source_connector` simulates source connector ingestion and stages markdown under KMS runtime paths.
- `act_on_candidate_knowledge` approves/rejects/flags candidates and can promote approved records to canonical knowledge.
- `approve_canonical_knowledge` updates approval status.
- `rollback_knowledge_version` resets canonical metadata to an earlier version where supported.
- `generate_context_package` and `generate_context_zip` package evidence for export.

## 7. LMS and Analytics Data Design

### LMS compatibility layer

`AIP/src/shared/lms.py` exposes:

- `get_lms_table(table_name)`
- `run_sqlite_query(sql, params)`

The implementation is PostgreSQL-backed. It lazily initializes tables when called, loads deterministic seed inputs from AIP-Infra if tables are empty, and translates legacy `?` parameters to PostgreSQL `%s` placeholders.

### Database Explorer

The DB Explorer micro-frontend calls:

- `GET /api/v1/analytics-data/tables`
- `GET /api/v1/analytics-data/tables/{table_name}/schema`
- `POST /api/v1/analytics-data/query`

It supports visual query filters, raw read-only SQL, result rendering, and JSON export.

## 8. Capability Registry

`shared.intelligence` owns capability registration and invocation.

At startup, `src/main.py` registers:

| Capability | Contract |
| --- | --- |
| `knowledge_retrieval` | Query KMS retrieval service and return grounded context/match count. |
| `context_management` | Get/set/clear session variables. |
| `summarization` | Produce dense summaries with LLM or deterministic fallback. |
| `narrative_generation` | Render KMS analytical templates with variables. |
| `metric_interpretation` | Calculate growth, mean, variance, z-score anomalies. |
| `visualization` | Build Vega-Lite specs from trend arrays. |
| `orchestration` | Execute ordered capability steps and traces. |
| `mcp_integration` | Simulate enterprise bridge calls such as Slack/PagerDuty. |

Each invocation logs:

- capability name
- input/output payload
- duration
- status
- active agent
- masked API key

## 9. Product Workflow Design

### Reporting

- PRISM parses direct metadata or uploaded files, normalizes SQL/schema, detects exact duplicates and overlaps.
- Report Builder keeps `ACTIVE_BUILD_SESSIONS` in memory, progresses six stages, handles rejected feedback, and publishes HTML files to `REPORT_PATH`.
- Conversational BI safely calls KMS/LMS/capabilities; optional infra failures degrade to explicit fallback output instead of failing the route.
- Proactive Insights uses metric interpretation over fixed trend baselines to produce alert objects.

### Business analytics

- Insight Discovery ranks segment volatility.
- RCA decomposes trend movements and can include LLM-guided agent commentary.
- What-if Analysis computes rate/asset/NPL sensitivities.
- Business Narratives generates targeted text for Slack/email/board memo style channels.

### Workflow automation

- Workflow Design validates schema, nodes, edges, cycles, disconnected nodes, capability availability, and missing templates.
- Workflow Orchestration executes DAG nodes in topological order, resolves dynamic input variables, supports HITL pauses, saves state in Redis, and returns traces.
- Task Automation executes queued code strings in a restricted subprocess style, tracks task history, and resumes approvals.
- Monitoring logs workflow runs/steps/artifacts to PostgreSQL and Neo4j lineage where available.

### Data science and ML

- Data Preparation analyzes columns/dataset shape/null readiness.
- Model Development returns experiment/champion metadata.
- Model Documentation builds validation/governance briefs.
- Model Pulse calculates drift signals and returns chart-ready telemetry.

## 10. Route Map

### Auth, data, and KMS

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | Unified analyst/SME login. |
| POST | `/api/v1/auth/sme-login` | Backward-compatible SME login alias. |
| POST | `/api/v1/auth/logout` | Clear active token session. |
| GET | `/api/v1/lms/query` | Query compatibility LMS tables. |
| GET | `/api/v1/analytics-data/tables` | List allowed analytics database tables. |
| GET | `/api/v1/analytics-data/tables/{table_name}/schema` | Inspect table schema. |
| POST | `/api/v1/analytics-data/query` | Run visual or raw read-only SQL query. |
| GET | `/api/v1/kms/domains` | List KMS business domains. |
| GET | `/api/v1/kms/options` | Populate KMS filter dropdowns. |
| GET | `/api/v1/knowledge/search` | Invoke knowledge retrieval capability. |
| GET | `/api/v1/knowledge/context` | Return context text only. |
| POST | `/api/v1/kms/upload` | Create candidate knowledge from document content. |
| POST | `/api/v1/kms/query` | Standard KMS query. |
| POST | `/api/v1/kms/query-advanced` | Advanced KMS retrieval with traces/filtering. |
| POST | `/api/v1/kms/retriever/download` | Download context package zip. |
| GET/POST | `/api/v1/kms/connectors` | List/create source connectors. |
| POST | `/api/v1/kms/connectors/sync` | Sync source connector. |
| GET | `/api/v1/kms/candidates` | List candidate knowledge. |
| POST | `/api/v1/kms/candidates/edit` | Edit candidate metadata. |
| POST | `/api/v1/kms/candidates/action` | Approve/reject/flag candidate. |
| GET | `/api/v1/kms/canonical` | List canonical knowledge. |
| POST | `/api/v1/kms/approve` | Approve/reject canonical knowledge. |
| POST | `/api/v1/kms/rollback` | Roll back canonical knowledge. |
| GET | `/api/v1/kms/observability` | KMS metrics/audit stats. |
| POST | `/api/v1/kms/context-package` | Return context package metadata. |

### Capabilities, logs, and workflows

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/v1/capabilities` | List registered capabilities. |
| POST | `/api/v1/capabilities/invoke` | Invoke capability by name. |
| GET/DELETE | `/api/v1/execution-logs` | Read/clear in-memory capability logs. |
| POST | `/api/v1/workflows/reporting/prism-lite` | Run PRISM from metadata payload. |
| POST | `/api/v1/workflows/reporting/prism/upload` | Upload files for PRISM screening. |
| POST | `/api/v1/workflows/reporting/build` | Legacy report build shortcut. |
| POST | `/api/v1/workflows/reporting/build/initiate` | Start report builder session. |
| POST | `/api/v1/workflows/reporting/build/step` | Advance report builder HITL step. |
| GET | `/api/v1/workflows/reporting/build/reports` | List published reports. |
| POST | `/api/v1/workflows/reporting/conversational-bi` | Conversational BI response. |
| GET | `/api/v1/workflows/reporting/proactive-insights` | Alert feed. |
| POST | `/api/v1/workflows/analytics/insight-discovery` | Segment insight discovery. |
| POST | `/api/v1/workflows/analytics/rca` | Root cause analysis. |
| POST | `/api/v1/workflows/analytics/what-if` | Scenario simulation. |
| POST | `/api/v1/workflows/analytics/business-narratives` | Narrative generation. |
| POST | `/api/v1/workflows/automation/run` | Validate and execute DAG. |
| GET | `/api/v1/workflows/automation/approvals` | List pending approvals. |
| POST | `/api/v1/workflows/automation/approve` | Resume/abort approval. |
| GET | `/api/v1/workflows/automation/telemetry` | Monitoring telemetry. |
| POST | `/api/v1/workflows/automation/tasks/submit` | Queue background code task. |
| GET | `/api/v1/workflows/automation/tasks/history` | Task execution history. |
| GET | `/api/v1/workflows/automation/monitoring/lineage` | Neo4j lineage query. |
| POST | `/api/v1/workflows/ds/prep` | Data preparation profile. |
| GET | `/api/v1/workflows/ds/experiments` | Experiment list. |
| POST | `/api/v1/workflows/ds/document` | Model documentation. |
| POST | `/api/v1/workflows/ds/model-pulse` | Model drift/pulse analysis. |

## 11. Static Mounts

`src/main.py` mounts:

- `/reports` -> `config.REPORT_PATH`
- `/ui/kms` -> `src/kms/ui`
- `/ui/reporting/prism`
- `/ui/reporting/report_building`
- `/ui/reporting/conversational_bi`
- `/ui/reporting/proactive_insights`
- `/ui/business_analytics/insight_discovery`
- `/ui/business_analytics/root_cause_analysis`
- `/ui/business_analytics/what_if_analysis`
- `/ui/business_analytics/business_narratives`
- `/ui/workflow_automation/workflow_design`
- `/ui/workflow_automation/workflow_orchestration`
- `/ui/workflow_automation/task_automation`
- `/ui/workflow_automation/monitoring`
- `/ui/data_science_ml/data_preparation`
- `/ui/data_science_ml/model_development`
- `/ui/data_science_ml/model_documentation`
- `/ui/data_science_ml/model_pulse`
- `/ui/db_explorer`
- `/` -> `src/ui`

## 12. Operational Considerations

- Start app from `AIP/start.sh`.
- Use `AIP/check.sh` to start/check Docker Compose and connectivity.
- Keep data and generated outputs in AIP-Infra.
- Do not store secrets in tracked files; `AIP-Infra/secrets` is a placeholder.
- Local auth sessions are in memory; process restart clears sessions.
- Capability execution logs are in memory; process restart clears logs.
- Report build sessions are in memory; published HTML persists in AIP-Infra reports storage.
