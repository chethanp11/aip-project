"""
Unit tests for the upgraded Workflow Automation Suite (Stateful Agentic AI)
"""

import os
import sys
import pytest
import asyncio
import time

# Ensure AIP/ and src/ are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AIP")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AIP/src")))

from src.workflow_automation.workflow_design.main import (
    WorkflowDAGBuilder,
    validate_dag_schema,
    validate_pipeline_config
)
from src.workflow_automation.workflow_orchestration.main import (
    run_custom_workflow,
    resolve_dynamic_variables,
    save_workflow_state_to_redis,
    load_workflow_state_from_redis
)
from src.workflow_automation.task_automation.main import (
    run_isolated_code_string,
    submit_background_task,
    get_task_history,
    resume_approval_workflow,
    paused_approvals
)
from src.workflow_automation.monitoring.main import (
    init_monitoring_tables,
    run_monitoring_workflow
)

# Register stateless capabilities manually for test framework context
from shared.intelligence import register_capability
import shared.capabilities.summarization as summarization_cap
import shared.capabilities.narrative_generation as narrative_generation_cap
import shared.capabilities.metric_interpretation as metric_interpretation_cap
import shared.capabilities.visualization as visualization_cap
import shared.capabilities.mcp_integration as mcp_integration_cap

register_capability('summarization', summarization_cap.config, summarization_cap.handler)
register_capability('narrative_generation', narrative_generation_cap.config, narrative_generation_cap.handler)
register_capability('metric_interpretation', metric_interpretation_cap.config, metric_interpretation_cap.handler)
register_capability('visualization', visualization_cap.config, visualization_cap.handler)
register_capability('mcp_integration', mcp_integration_cap.config, mcp_integration_cap.handler)

# ==========================================================================
# ⚡ 1. WORKFLOW DESIGN & CYCLE VALIDATION TESTS
# ==========================================================================
def test_workflow_dag_builder():
    """Verifies that the modular configuration builder correctly aggregates independent tasks."""
    builder = WorkflowDAGBuilder("LDR Liquidity Pipeline", "Aggregates LDR tasks")
    builder.add_node("node_retrieve", "knowledge_retrieval", {"question": "LDR limit"})
    builder.add_node("node_interpret", "metric_interpretation", {"metricId": "ldr_ratio"})
    builder.add_edge("node_retrieve", "node_interpret")
    
    dag = builder.build()
    
    assert dag['name'] == "LDR Liquidity Pipeline"
    assert len(dag['nodes']) == 2
    assert len(dag['edges']) == 1
    assert dag['nodes'][0]['id'] == "node_retrieve"
    assert dag['nodes'][1]['id'] == "node_interpret"

def test_dag_cycle_detection():
    """Verifies that cycle checking algorithm properly catches loops and validates straight graphs."""
    # 1. Valid linear sequence (No loops)
    dag_valid = {
        "workflow_id": "wf_valid_run",
        "name": "Valid Linear",
        "nodes": [
            {"id": "n1", "capability": "summarization"},
            {"id": "n2", "capability": "narrative_generation"}
        ],
        "edges": [
            {"source": "n1", "target": "n2"}
        ]
    }
    validation = validate_dag_schema(dag_valid)
    assert validation['structuralValid'] is True
    
    # 2. Cyclic loop (Cycle detected)
    dag_cyclic = {
        "workflow_id": "wf_cyclic_run",
        "name": "Cyclic Loop",
        "nodes": [
            {"id": "n1", "capability": "summarization"},
            {"id": "n2", "capability": "narrative_generation"}
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n1"}
        ]
    }
    validation = validate_dag_schema(dag_cyclic)
    assert validation['structuralValid'] is False
    assert any("Cyclic dependency loop detected" in err for err in validation['errors'])

def test_capability_boundary_checking():
    """Verifies that unregistered capabilities raise structural validation schema warnings."""
    dag_invalid_cap = {
        "workflow_id": "wf_cap_bound",
        "name": "Invalid Capability",
        "nodes": [
            {"id": "n1", "capability": "malicious_eval_unregistered"}
        ],
        "edges": []
    }
    validation = validate_dag_schema(dag_invalid_cap)
    assert validation['structuralValid'] is False
    assert any("not registered" in err for err in validation['errors'])

# ==========================================================================
# ⚡ 2. DYNAMIC PARAMETER RESOLUTION & VALUE DATA BLOCK ROUTES
# ==========================================================================
def test_resolve_dynamic_variables():
    """Verifies dynamic variable routing parses parameters and replaces values correctly."""
    data_blocks = {
        "step_task": {
            "summary": "This is a regulatory sweep briefing.",
            "metric": 1.45
        }
    }
    
    # Native value replacement
    resolved_exact = resolve_dynamic_variables("{{step_task.metric}}", data_blocks)
    assert resolved_exact == 1.45
    
    # String interpolation replacement
    resolved_str = resolve_dynamic_variables("Status: {{step_task.summary}} Value: {{step_task.metric}}", data_blocks)
    assert resolved_str == "Status: This is a regulatory sweep briefing. Value: 1.45"

# ==========================================================================
# ⚡ 3. STATEFUL ORCHESTRATION & TRANSITIONAL REDIS CACHING TESTS
# ==========================================================================
@pytest.mark.anyio
async def test_langgraph_orchestrator_execution():
    """Tests the dynamic LangGraph state graph runner executing sequential registered capabilities."""
    dag = {
        "workflow_id": "wf_langgraph_run",
        "name": "LangGraph Sequential",
        "nodes": [
            {"id": "n1", "capability": "summarization", "input": {"text": "AIP is an enterprise intelligence layer."}},
            {"id": "n2", "capability": "narrative_generation", "input": {
                "templateId": "briefing_brief",
                "variables": {
                    "summaryText": "{{n1.summary}}"
                }
            }}
        ],
        "edges": [
            {"source": "n1", "target": "n2"}
        ]
    }
    
    validation = validate_pipeline_config(dag)
    assert validation['structuralValid'] is True
    
    res = await run_custom_workflow(dag)
    assert res['paused'] is False
    assert res['success'] is True
    assert len(res['traces']) == 2
    assert res['traces'][0]['stepId'] == "n1"
    assert res['traces'][1]['stepId'] == "n2"

@pytest.mark.anyio
async def test_langgraph_redis_pause_and_resume():
    """Validates the Redis transient caching and manual approval gate resume routes."""
    dag = {
        "workflow_id": "wf_redis_pause",
        "name": "Pause and Resume",
        "nodes": [
            {"id": "n1", "capability": "summarization", "input": {"text": "Auditing sweeps."}},
            {"id": "n2", "capability": "mcp_integration", "input": {
                "serverName": "slack",
                "toolName": "post_message",
                "arguments": {"channel": "#alerts", "text": "Resumed alert"}
            }, "requireApproval": True}
        ],
        "edges": [
            {"source": "n1", "target": "n2"}
        ]
    }
    
    # 1. Run (Expect execution to pause at node n2)
    res = await run_custom_workflow(dag)
    assert res['paused'] is True
    assert "approvalId" in res
    
    app_id = res['approvalId']
    
    # 2. Verify state cached in Redis
    cached = load_workflow_state_from_redis(app_id)
    assert cached is not None
    assert cached['paused'] is True
    assert cached['current_node'] == "n2"
    
    # 3. Resume the gate run
    resume_res = await resume_approval_workflow(app_id, approved=True)
    assert resume_res['success'] is True
    assert resume_res['paused'] is False
    assert len(resume_res['traces']) >= 2
    assert resume_res['traces'][0]['stepId'] == "step_manual_approval"
    assert resume_res['traces'][0]['status'] == "approved"

# ==========================================================================
# ⚡ 4. BACKGROUND TASK ISOLATION & SUBPROCESS SANDBOXING TESTS
# ==========================================================================
@pytest.mark.anyio
async def test_run_isolated_code_string():
    """Verifies that user-provided code strings execute safely in isolated Python subprocess sandboxes."""
    code = "import sys\nprint('Sandbox Execution Verified')\nsys.exit(0)"
    res = run_isolated_code_string(code, "test_sandbox")
    
    assert res['success'] is True
    assert "Sandbox Execution Verified" in res['stdout']
    assert res['stderr'] == ""
    assert res['durationMs'] > 0
    assert os.path.exists(res['tempFile'])

@pytest.mark.anyio
async def test_async_background_task_runner():
    """Verifies that asynchronously enqueued background tasks process cleanly and generate physical storage artifacts."""
    code = "print('Async Background Verification')"
    task_id = "test_async_task"
    
    # Enqueue task
    submit_background_task(task_id, "schedule_trigger", code)
    
    # Allow worker processing latency
    await asyncio.sleep(0.5)
    
    history = get_task_history()
    matched = [h for h in history if h['id'] == task_id]
    
    # Task should have run
    assert len(matched) == 1
    assert matched[0]['status'] in ['completed', 'running']
    
    # Verify that a physical artifact was saved under StorageClient directory structure
    from shared.infra.storage_client import StorageClient
    storage = StorageClient()
    artifact_path = os.path.join(storage.get_artifacts_dir(), f"task_artifact_{task_id}.txt")
    
    # Allow serialization write latency
    await asyncio.sleep(0.5)
    assert os.path.exists(artifact_path)
    
    with open(artifact_path, 'r') as f:
        content = f.read()
        assert "TASK AUTOMATION REPORT" in content
        assert "Async Background Verification" in content

# ==========================================================================
# ⚡ 5. OBSERVABILITY TRACING & METRICS AGGREGATION TESTS
# ==========================================================================
@pytest.mark.anyio
async def test_observability_logging_and_tracing():
    """Verifies telemetry metrics insertion and Neo4j graph lineage updates function without direct cursors."""
    from src.workflow_automation.monitoring.main import log_orchestrator_run, log_orchestrator_step
    
    wf_id = "wf_monitoring_test"
    wf_name = "Observability Verification"
    
    # Log step metrics and run aggregates
    await log_orchestrator_step(wf_id, "step_init", 120, "completed", {"status": "ok"})
    await log_orchestrator_run(wf_id, wf_name, "completed", [
        {"stepId": "step_init", "capability": "summarization", "status": "completed", "durationMs": 120}
    ])
    
    # Check Postgres database aggregates
    stats = await run_monitoring_workflow()
    assert "metrics" in stats
    assert stats['metrics']['totalInvocations'] > 0
    assert "successRate" in stats['metrics']
    assert "avgLatency" in stats['metrics']

@pytest.mark.anyio
async def test_new_api_routes():
    """Verifies that the new API gateway routes for background tasks and Neo4j lineage function correctly."""
    from src.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    headers = {"Authorization": "Bearer AIP-TEST-SESSION-KEY"}
    
    # 1. Submit task route
    task_payload = {
        "taskId": "api_task_test",
        "trigger": "manual_run",
        "code": "print('API sandbox route verified')"
    }
    res_sub = client.post("/api/v1/workflows/automation/tasks/submit", json=task_payload, headers=headers)
    assert res_sub.status_code == 200
    assert res_sub.json()['success'] is True
    assert res_sub.json()['taskId'] == "api_task_test"
    
    # 2. History route
    res_hist = client.get("/api/v1/workflows/automation/tasks/history", headers=headers)
    assert res_hist.status_code == 200
    assert isinstance(res_hist.json(), list)
    
    # 3. Neo4j Lineage route
    res_lin = client.get("/api/v1/workflows/automation/monitoring/lineage", headers=headers)
    assert res_lin.status_code == 200
    assert isinstance(res_lin.json(), list)
