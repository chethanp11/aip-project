---
name: AIP Security and RBAC
description: Guidelines for enforcing data confidentiality hierarchy, role-based retrieval segregation, and transactional security audit logs.
---

# Skill: AIP Security and RBAC

## 📌 Context
Confidentiality and governance are core pillars of the AIM Intelligence Platform. The application segment must prevent data leaks or unauthorized regulatory actions. This skill guides agents on implementing role verification, clearance checks, and security auditing.

---

## 📐 Implementation Guidelines

### 1. Clearance Level Hierarchy Verification
- Define the standard clearance rankings and map user session properties accordingly:
  ```python
  CLEARANCE_LEVELS = {
      'Public': 0,
      'Internal': 1,
      'Confidential': 2,
      'Restricted': 3
  }
  ```
- **Filter Evaluation Logic**:
  - When compiling vectors or graph neighbors, resolve the user's `security_clearance` level.
  - Reject or drop any node where:
    ```python
    node_level = CLEARANCE_LEVELS.get(node_classification, 1)
    user_level = CLEARANCE_LEVELS.get(user_clearance, 1)
    if node_level > user_level:
        # Silently exclude or log block trace
        continue
    ```

### 2. Role-Based Access Control Policies
- **Analyst Boundary**:
  - Limit Analyst retrieval strictly to approved canonical knowledge records (`approval_status == 'Approved'`).
  - Block attempts by Analysts to view, edit, or approve draft candidates.
- **SME Boundary**:
  - Allow access to both candidate draft elements (`candidate_knowledge`) and canonical nodes.
  - Empower SMEs to perform administrative actions: editing domain metadata, tags, relationships, approving records into canonical status, or rolling back configurations to older database index snapshots.

### 3. Traceability & Security Auditing
- Every query retrieval transaction, SME approval action, or candidate creation task must log an event to the `security_audit_logs` table.
- **Parameters to Record**:
  - `log_id`: Unique identifier (e.g. standard UUID).
  - `timestamp`: Current ISO string.
  - `action`: The operations name (e.g. `QUERY_advanced_retrieval`, `APPROVE_canonical_knowledge`).
  - `user_role`: Active calling role (`Analyst` or `SME`).
  - `knowledge_id`: Target entity ID if applicable.
  - `status`: Result of validation check (`Success` or `Blocked`).
