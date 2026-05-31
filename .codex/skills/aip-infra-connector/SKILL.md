---
name: AIP Infrastructure Connector
description: Guide for executing connection queries, transactional data synchronization, and path operations against PostgreSQL, Neo4j, and Redis infrastructure.
---

# Skill: AIP Infrastructure Connector

## 📌 Context
In the AIM Intelligence Platform (AIP), high-availability database engines power all semantic search and banking ledger data lookups. This skill guides developer agents on how to interface with PostgreSQL, Neo4j, Redis, and file systems through our centralized infrastructure clients.

---

## 📐 Implementation Guidelines

### 1. PostgreSQL Client Operations
- **Import Client Wrapper**:
  ```python
  from src.shared.infra_client.postgres_client import PostgresClient
  ```
- **Placeholders Emulation**:
  - Always use standard `execute_query` or `execute_many`.
  - The driver automatically replaces SQLite `?` placeholders with `%s` to keep API queries compatible.
- **SQLite "INSERT OR REPLACE" mapping**:
  - PostgreSQL does not natively support `INSERT OR REPLACE`. 
  - Our internal wrappers translate this by running an explicit `DELETE FROM table WHERE key = value` followed by a standard `INSERT`. Keep query structures standard so that the wrapper can catch and translate them.

### 2. Neo4j Cypher Traversal
- **Import Client**:
  ```python
  from src.shared.infra_client.neo4j_client import Neo4jClient
  ```
- **Merging Nodes**:
  - Set up entities using `MERGE` to prevent duplicate nodes:
    ```cypher
    MERGE (n:KnowledgeNode {node_id: $node_id})
    SET n.type = $type, n.title = $title, n.content = $content
    ```
- **Traversing Hops**:
  - Fetch neighboring regulations, policies, or related metrics by matching edges:
    ```cypher
    MATCH (source:KnowledgeNode {node_id: $source_id})-[r:RELATED]->(target:KnowledgeNode)
    RETURN target.node_id, target.title, r.relationship
    ```

### 3. Redis Cache & Session Tracking
- **Import Client**:
  ```python
  from src.shared.infra_client.redis_client import RedisClient
  ```
- **Usage**:
  - Keep workflow rate limits, session tokens, and telemetry logs cached using lightweight Redis structures.
  - Set explicit TTL values to avoid filling memory space.

### 4. Storage Operations (StorageClient)
- **Import Client**:
  ```python
  from src.shared.infra_client.storage_client import StorageClient
  ```
- **Write Actions**:
  - Write output reports or analysis archives outside the application workspace (`Infra/storage/{reports,artifacts}`).
  - Maintain config mapping absolute root definitions rather than relative path operations.
