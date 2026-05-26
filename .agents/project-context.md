# AIM Intelligence Platform (AIP) Project Context

## 📌 Overview
The **AIM Intelligence Platform (AIP)** is an enterprise-grade analytics intelligence platform that serves as a cognitive layer bridging data warehouses, structured knowledge repositories, and automated business workflows. 

AIP separates execution, reasoning, and semantic knowledge into three clean modular layers:
1. **Knowledge Management System (KMS)**: Git-managed declarative files representing metrics trees, data lineages, glossaries, and templates, backed by a hybrid vector-and-graph search engine (PostgreSQL + Neo4j).
2. **Intelligence Layer**: Shared, stateless cognitive capabilities, request-scoped context management, prompt structures, and external Model Context Protocol (MCP) integrations.
3. **Data Layer**: Direct access to enterprise banking datasets (LMS data) served through Postgres/SQL databases without third-party external integrations.

---

## 🏗️ Platform Architecture & Folder Structure

```text
/Users/chethan/GitHub/AIP-Project/
├── AIP/                          # Python Application Runtime (FastAPI)
│   ├── src/
│   │   ├── main.py               # API Gateway router, static UI and report mounts
│   │   ├── shared/
│   │   │   ├── config/config.py  # Path mappings and centralized credentials loaders
│   │   │   ├── infra/            # PostgresClient, Neo4jClient, RedisClient, StorageClient
│   │   │   ├── capabilities/     # Stateless reusable capability handlers
│   │   │   ├── intelligence.py   # Registry and thread-safe active_agent_context
│   │   │   └── lms.py            # Local Banking / LMS database queries
│   │   ├── kms/                  # KMS ingestion, advanced retrieval and search endpoints
│   │   ├── reporting/            # Stateful Reporting workflows (PRISM, Builder, ConvBI)
│   │   ├── business_analytics/   # Stateful Business Analytics (Insight Discovery, RCA, What-if)
│   │   ├── workflow_automation/  # Stateful Automation (Builders, approvals, monitoring)
│   │   └── data_science_ml/      # Stateful DS/ML workflows (Prep, Documentation, Pulse)
└── AIP-Infra/                    # External Infrastructure Surfaces
    ├── docker/                   # Docker Compose services (Postgres, Neo4j, Redis)
    └── storage/                  # Out-of-app data directories (kms seeds, lms seeds, logs)
```

---

## 🔒 Session & Security Parameters
- All routes under `/api/v1` (excluding authentication and public static files) require a bearer token starting with `AIP-`.
- Default KMS bootstrap credentials (seeded automatically in PostgreSQL):
  - **Analyst User**: `analyst` / `password` (issues `AIP-ANALYST-SESSION-...` tokens)
  - **SME User**: `sme` / `password` (issues `AIP-SME-SESSION-...` tokens)
- Role-based Access Control (RBAC):
  - **Analyst**: Accesses approved canonical knowledge. Restricted from draft candidates or unapproved regulations.
  - **SME**: Direct governance rights (reviewing candidates, editing, approving, or rolling back canonical entries).

---

## ⚙️ Shared Platform Integration Rules
- Workflows must **never** write directly to raw database drivers or local volumes. They must use the reusable clients under `src/shared/infra`.
- Capabilities are **stateless and idempotent**. They do not maintain session variables or write temporary local files.
- Configuration parameters and physical storage paths are always sourced from `src.shared.config.config`.
