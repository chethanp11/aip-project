---
name: AIP Workflow Composer
description: Guide for composing stateful product workflows in suites by invoking registered core capabilities.
---

# Skill: AIP Workflow Composer

## 📌 Context
In the AIM Intelligence Platform (AIP), a **Workflow** represents a stateful, product-specific analytical process composed of sequential capability executions. They reside under `/workflows/` and correspond to user-facing products (e.g. Conversational BI, Root Cause Analysis, Model Pulse).

---

## 📐 Composition Guidelines

### 1. Separation of Concerns
*   Workflows are **stateful**: They manage active session parameters, log execution progress, read uploaded files, and trigger alerts.
*   Workflows **do not contain core logic**: Any statistical, visualization, or retrieval task must be routed to the appropriate capability by importing `invoke_capability` from `platform-core/intelligence.js`.

### 2. Invocation Pattern
To compose a pipeline, import the shared capability invoker and execute calls sequentially:
```javascript
import { invoke_capability } from '../../platform-core/intelligence.js';

export async function your_workflow(params) {
  // Step 1: Retrieval Grounding facts from KMS
  const kmsData = await invoke_capability('knowledge_retrieval', { question: params.q });
  
  // Step 2: Metric statistical analysis
  const stats = await invoke_capability('metric_interpretation', {
    metricId: params.id,
    trends: params.trends,
    analysisType: 'anomaly'
  });
  
  // Step 3: Outbound notification alert
  const alert = await invoke_capability('mcp_integration', {
    serverName: 'slack',
    toolName: 'post_message',
    arguments: { channel: '#alerts', text: stats.explanation }
  });
  
  return {
    success: true,
    stats,
    alert
  };
}
```

### 3. Step Logging & Errors Handling
*   Wrap capability invocations in structured `try...catch` blocks to track failed nodes in the execution logs table.
*   Dispatches notifications on pipeline exceptions and logs duration parameters for every run.
