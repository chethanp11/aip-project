---
name: AIP Capability Builder
description: Guide for creating stateless, reusable core capabilities conforming to standard JSON-schema boundaries.
---

# Skill: AIP Capability Builder

## 📌 Context
In the AIM Intelligence Platform (AIP), a **Capability** represents a stateless, atomic, highly reusable cognitive or utility operation. They reside under `/capabilities/` and are registered dynamically in the shared Intelligence Layer registry.

---

## 📐 Implementation Guidelines

### 1. File Structure
Every capability directory must contain:
```text
capabilities/your-capability/
├── index.js     # Exports default capability object
└── README.md    # API schemas & descriptions
```

### 2. Code Interface Model
Your `index.js` must export a default object conforming to this exact contract:
```javascript
export default {
  name: 'your_capability_name',
  config: {
    description: 'Concise explanation of the capability.',
    inputSchema: {
      // JSON Schema matching inputs parameters
    },
    outputSchema: {
      // JSON Schema matching output parameters
    }
  },
  handler: async (input) => {
    // 1. Validate inputs
    // 2. Run stateless logic
    // 3. Return output object matching outputSchema
  }
};
```

### 3. Core Constraints
*   **Idempotency & Statelessness**: Capabilities must be strictly side-effect free. They must never write local files, update session lists, or mutate global variables.
*   **Decoupled Dependencies**: Never import one capability directory directly into another. All communication must occur through the Orchestration capability or from stateful workflows.
*   **Central Registration**: Ensure that your new capability is imported and registered using `register_capability()` inside `/platform-core/server.js` at boot time.
