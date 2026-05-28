"""
Product 10: Workflow Orchestration Engine (Stateful Agentic AI)
Assigned Enterprise Agent: Platform Routing Agent
"""

import time
import random
import string
import json
import re
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, START, END
from shared.intelligence import invoke_capability
from shared.infra.redis_client import RedisClient
from src.workflow_automation.task_automation.main import paused_approvals

# ==========================================================================
# 🚦 STATE DEFINITIONS & TYPES FOR STATEFUL RUNNERS
# ==========================================================================
class WorkflowState(TypedDict):
    workflow_id: str
    name: str
    dag: Dict[str, Any]
    traces: List[Dict[str, Any]]
    data_blocks: Dict[str, Any]
    paused: bool
    approval_id: str
    current_node: str
    success: bool
    error: str

# ==========================================================================
# 🔑 CACHING LAYERS: DYNAMIC REDIS SYNC
# ==========================================================================
def save_workflow_state_to_redis(session_id: str, state: Dict[str, Any]):
    """Caches transient workflow state blocks inside the shared aip-redis cache."""
    try:
        r = RedisClient().get_client()
        r.set(f"aip:session:{session_id}", json.dumps(state))
        print(f"[Orchestrator: Redis Cache] Cached transient workflow session: aip:session:{session_id}")
    except Exception as e:
        print(f"[Orchestrator: Redis Cache Error] Could not synchronize state with Redis client: {e}")

def load_workflow_state_from_redis(session_id: str) -> Dict[str, Any]:
    """Retrieves cached transient workflow session state from the shared aip-redis cache."""
    try:
        r = RedisClient().get_client()
        data = r.get(f"aip:session:{session_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        print(f"[Orchestrator: Redis Cache Error] Could not retrieve session state from Redis: {e}")
    return None

# ==========================================================================
# 🛠️ STATE ROUTING: DYNAMIC VARIABLE SUBSTITUTION
# ==========================================================================
def resolve_dynamic_variables(val: Any, data_blocks: Dict[str, Any]) -> Any:
    """Recursively resolves template variables of the format {{node_id.key}} from previous step data blocks."""
    if isinstance(val, str):
        matches = re.findall(r'\{\{([^}]+)\}\}', val)
        if not matches:
            return val
            
        # Single exact variable replacement returning native type
        if len(matches) == 1 and val.strip() == f"{{{{{matches[0]}}}}}":
            path = matches[0].split('.')
            return get_nested_value(data_blocks, path)
            
        # Inline string interpolation
        new_str = val
        for m in matches:
            path = m.split('.')
            resolved = get_nested_value(data_blocks, path)
            new_str = new_str.replace(f"{{{{{m}}}}}", str(resolved or ''))
        return new_str
        
    elif isinstance(val, dict):
        return {k: resolve_dynamic_variables(v, data_blocks) for k, v in val.items()}
    elif isinstance(val, list):
        return [resolve_dynamic_variables(x, data_blocks) for x in val]
    return val

def get_nested_value(d: Dict[str, Any], path: List[str]) -> Any:
    """Safely extracts nested dictionary values following a dot-separated path."""
    curr = d
    for p in path:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        else:
            return None
    return curr

# ==========================================================================
# 🛠️ TOPOLOGICAL SEQUENCER FOR CYCLIC/DAG RESOLUTION
# ==========================================================================
def get_topological_order(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
    """Generates a topologically sorted execution order of node IDs for the DAG."""
    node_ids = [n['id'] for n in nodes]
    adj = {n_id: [] for n_id in node_ids}
    in_degree = {n_id: 0 for n_id in node_ids}
    
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if src in adj and tgt in adj:
            adj[src].append(tgt)
            in_degree[tgt] += 1
            
    queue = [n_id for n_id in node_ids if in_degree[n_id] == 0]
    order = []
    
    while queue:
        u = queue.pop(0)
        order.append(u)
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                
    # Return topological order, appending remaining if disconnected nodes exist
    for n_id in node_ids:
        if n_id not in order:
            order.append(n_id)
            
    return order

# ==========================================================================
# 🚦 LANGGRAPH STATEFUL GRAPH RUNNER ENGINE
# ==========================================================================
def make_langgraph_node_func(node_id: str, capability: str, input_template: Dict[str, Any], require_approval: bool):
    """Factory creating stateless graph node functions executing specific shared capabilities."""
    async def node_func(state: WorkflowState) -> Dict[str, Any]:
        # Short-circuit if workflow is paused or marked as failed
        if state.get('paused') or not state.get('success', True):
            return {}
            
        # Idempotency check: skip execution if this step has already completed successfully
        if node_id in state.get('data_blocks', {}):
            print(f"[Orchestrator: LangGraph] Step '{node_id}' already completed in a previous leg. Skipping.")
            return {}
            
        resumed_node = state.get('current_node', '')
        
        # Enforce manual approval routing gate
        if require_approval and state.get('approval_id') is None and resumed_node != f"{node_id}_resumed":
            approval_id = 'app_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
            print(f"[Orchestrator: LangGraph] Pausing workflow at step '{node_id}' for manual approval. ID: {approval_id}")
            return {
                'paused': True,
                'approval_id': approval_id,
                'current_node': node_id
            }
            
        start_time = time.time()
        resolved_input = resolve_dynamic_variables(input_template, state.get('data_blocks', {}))
        
        try:
            print(f"[Orchestrator: LangGraph] Invoking capability '{capability}' for node '{node_id}'")
            output = await invoke_capability(capability, resolved_input)
            duration_ms = int((time.time() - start_time) * 1000)
            
            new_data = dict(state.get('data_blocks', {}))
            new_data[node_id] = output
            
            trace = {
                'stepId': node_id,
                'capability': capability,
                'status': 'completed',
                'durationMs': duration_ms,
                'output': output
            }
            
            # Post telemetry update using monitoring utility
            from src.workflow_automation.monitoring.main import log_orchestrator_step
            await log_orchestrator_step(state.get('workflow_id'), node_id, duration_ms, 'completed', output)
            
            return {
                'data_blocks': new_data,
                'traces': state.get('traces', []) + [trace],
                'current_node': f"{node_id}_completed",
                'approval_id': None, # Clear active gate
                'success': True
            }
        except Exception as error:
            duration_ms = int((time.time() - start_time) * 1000)
            trace = {
                'stepId': node_id,
                'capability': capability,
                'status': 'failed',
                'durationMs': duration_ms,
                'error': str(error)
            }
            
            from src.workflow_automation.monitoring.main import log_orchestrator_step
            await log_orchestrator_step(state.get('workflow_id'), node_id, duration_ms, 'failed', {'error': str(error)})
            
            print(f"[Orchestrator: LangGraph] Step '{node_id}' failed: {error}")
            return {
                'traces': state.get('traces', []) + [trace],
                'current_node': node_id,
                'success': False,
                'error': str(error)
            }
            
    return node_func

async def run_dag_orchestrator(dag: Dict[str, Any], initial_state: Dict[str, Any] = None) -> Dict[str, Any]:
    """Compiles and runs a standard Directed Acyclic Graph structure inside the LangGraph engine."""
    workflow_id = dag['workflow_id']
    name = dag['name']
    nodes = dag.get('nodes', [])
    edges = dag.get('edges', [])
    
    # Topological sequencing
    order = get_topological_order(nodes, edges)
    if not order:
        return {'success': False, 'error': 'Empty workflow topology.'}
        
    # Build LangGraph StateGraph
    builder = StateGraph(WorkflowState)
    
    # Map steps to nodes
    for node in nodes:
        n_id = node['id']
        builder.add_node(
            n_id,
            make_langgraph_node_func(
                n_id,
                node['capability'],
                node.get('input', {}),
                node.get('requireApproval', False)
            )
        )
        
    # Set sequential topological execution path
    for i in range(len(order) - 1):
        builder.add_edge(order[i], order[i+1])
        
    builder.set_entry_point(order[0])
    builder.add_edge(order[-1], END)
    
    graph = builder.compile()
    
    # Setup initial state dictionary
    state_input: WorkflowState = {
        'workflow_id': workflow_id,
        'name': name,
        'dag': dag,
        'traces': [],
        'data_blocks': {},
        'paused': False,
        'approval_id': '',
        'current_node': '',
        'success': True,
        'error': ''
    }
    
    # Override with previous state inputs if resuming
    if initial_state:
        state_input.update(initial_state)
        
    print(f"[Orchestrator: LangGraph] Starting execution loop for workflow '{name}' ({workflow_id})")
    
    # Run the compiled LangGraph State Machine
    final_state = await graph.ainvoke(state_input)
    
    # Handle paused state
    if final_state.get('paused'):
        approval_id = final_state.get('approval_id')
        paused_node = final_state.get('current_node')
        
        # Save to Redis transient cache
        save_workflow_state_to_redis(approval_id, final_state)
        
        # Backward compatibility registration in memory approvals list
        approval_task = {
            'id': approval_id,
            'name': name,
            'step': f"Approval Gate: Node {paused_node}",
            'status': 'paused',
            'created': time.strftime('%H:%M:%S', time.localtime()),
            'config': {
                'workflow_id': workflow_id,
                'name': name,
                'dag': dag,
                'paused_node': paused_node,
                'requireApproval': True
            }
        }
        paused_approvals.append(approval_task)
        
        # Record monitoring telemetry run log
        from src.workflow_automation.monitoring.main import log_orchestrator_run
        await log_orchestrator_run(workflow_id, name, 'paused', final_state.get('traces', []))
        
        return {
            'paused': True,
            'approvalId': approval_id,
            'traces': final_state.get('traces', [])
        }
        
    # Save completed execution trace and metadata
    status = 'completed' if final_state.get('success') else 'failed'
    from src.workflow_automation.monitoring.main import log_orchestrator_run
    await log_orchestrator_run(workflow_id, name, status, final_state.get('traces', []))
    
    return {
        'paused': False,
        'success': final_state.get('success', False),
        'traces': final_state.get('traces', [])
    }

async def run_custom_workflow(config: Dict[str, Any]) -> Dict[str, Any]:
    """Orchestrates custom alerts, falling back to dynamic DAG compilation if simple flat parameters are supplied."""
    
    # If the design validator has compiled a DAG layout under the hood
    if 'dag' in config:
        return await run_dag_orchestrator(config['dag'])
        
    # If direct custom DAG payload is supplied
    if 'nodes' in config and 'edges' in config:
        return await run_dag_orchestrator(config)
        
    # Basic backwards compatibility fallback if validation did not compile a DAG
    name = config.get('name', 'Custom Alert') or 'Custom Alert'
    trigger = config.get('trigger', 'weekly_schedule')
    task = config.get('task', 'profile')
    notification = config.get('notification', 'slack')
    require_approval = config.get('requireApproval', False)
    
    from src.workflow_automation.workflow_design.main import WorkflowDAGBuilder
    builder = WorkflowDAGBuilder(name, f"Standard Flat alert triggered by {trigger}")
    
    # Compile simple settings to DAG
    task_id = "step_task"
    task_cap = "metric_interpretation" if task == 'profile' else "summarization"
    task_input = {
        "metricId": "npl_ratio",
        "trends": [1.42, 1.45, 1.38, 1.49, 1.55, 1.62, 1.85],
        "analysisType": "anomaly"
    } if task == 'profile' else {
        "text": "Enterprise automation trigger has initiated successfully. Initial balance checks verified with zero regulatory flags."
    }
    builder.add_node(task_id, task_cap, task_input)
    
    narrative_id = "step_narrative"
    builder.add_node(narrative_id, "narrative_generation", {
        "templateId": "briefing_brief",
        "variables": {
            "metricName": "LDR Liquidity Pipeline",
            "metricValue": "85.8%",
            "compareValue": "82.5%",
            "metricFormula": "loan_to_deposit_ratio",
            "explanation": f"Custom workflow triggered via event: {trigger}",
            "summaryText": "Automatic alert created via user-configured DAG notification rules."
        }
    })
    builder.add_edge(task_id, narrative_id)
    
    notify_id = "step_notify"
    builder.add_node(notify_id, "mcp_integration", {
        "serverName": "slack" if notification == "slack" else "pagerduty",
        "toolName": "post_message" if notification == "slack" else "trigger_incident",
        "arguments": {
            "channel": "#enterprise-alerts",
            "text": f"🔔 Custom Workflow [{name}] triggered immediately! Pipeline executed task [{task}] successfully."
        }
    }, require_approval=require_approval)
    builder.add_edge(narrative_id, notify_id)
    
    dag = builder.build()
    return await run_dag_orchestrator(dag)
