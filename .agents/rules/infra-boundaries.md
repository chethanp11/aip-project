# Infrastructure Boundaries & Storage Rules

This document outlines the strict physical boundaries and data integration models between the application runtime (`AIP/`) and external storage/database layers (`AIP-Infra/`).

---

## 🚫 1. Code/Storage Separation Policies
- **No Embedded Knowledge Assets**: Raw metric seed files, glossary JSON files, analytical templates, or banking reference datasets must **never** be placed inside application package trees.
- **Physical Boundary Mapping**:
  - Code/Endpoints: Reside exclusively in `AIP/src/`.
  - Seeds/Dynamic files: Reside exclusively in `AIP-Infra/storage/` (specifically `storage/kms/seeds/`, `storage/lms/seeds/`, `storage/reports/`, etc.).
  - Logs: Written exclusively to `AIP-Infra/logs/`.
- **Config-Driven Absolute Paths**:
  - Workflows and capabilities must never construct hardcoded absolute physical paths or rely on relative `../../` file directory lookups.
  - Always import `src.shared.config.config` and use its predefined, environment-mapped parameters:
    - `config.KMS_SEED_PATH` for seeds/reference blueprints.
    - `config.REPORT_PATH` for saving generated/published business briefings.
    - `config.LOG_PATH` for logging pipeline errors or ingestion activities.

---

## 💾 2. Infrastructure Client Connection Models
- **Database Client Wrappers**:
  - Always leverage the centralized connection client classes under `src.shared.infra` instead of writing custom psycopg2, redis, or neo4j connections.
  - **PostgresClient**: Handles connection pooling and executes standard SQL commands. Converts SQLite-compatible parameter symbols (`?`) to Postgres positional tokens (`%s`). Emulates SQLite `INSERT OR REPLACE INTO` behavior safely.
  - **Neo4jClient**: Handles bolt connections to the Neo4j instance for Graph traversal.
  - **RedisClient**: Manages sessions and system cache storage.
  - **StorageClient**: Manages physical writes of dynamic artifacts outside the app tree.

---

## 🔌 3. Ingestion & Retrieval Path Boundaries
- Product workflows must remain decoupled from physical database details.
- To retrieve grounded metrics context or perform semantic searches:
  - Call the shared stateless capability `knowledge_retrieval` or invoke the `RetrievalClient` abstraction.
  - Do not bypass this route by writing direct file reads from `AIP/src/kms/data/` or writing custom raw SQL queries directly inside reporting/analytics workflow directories.
