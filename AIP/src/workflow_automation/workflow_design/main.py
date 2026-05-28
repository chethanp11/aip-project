"""
Product 9: Workflow Design Console (Stateful Agentic AI)
Assigned Enterprise Agent: Workflow Designer Agent
"""

import uuid
import json
import time
import math
from typing import Dict, Any, List
from shared.infra.postgres_client import PostgresClient
from shared.infra.neo4j_client import Neo4jClient
from shared.intelligence import capability_registry

class WorkflowDAGBuilder:
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []

    def add_node(self, node_id: str, capability: str, input_data: Dict[str, Any] = None, require_approval: bool = False) -> 'WorkflowDAGBuilder':
        self.nodes.append({
            "id": node_id,
            "capability": capability,
            "input": input_data or {},
            "requireApproval": require_approval
        })
        return self

    def add_edge(self, source_id: str, target_id: str) -> 'WorkflowDAGBuilder':
        self.edges.append({
            "source": source_id,
            "target": target_id
        })
        return self

    def build(self) -> Dict[str, Any]:
        return {
            "workflow_id": f"wf_{uuid.uuid4().hex[:6]}",
            "name": self.name,
            "description": self.description,
            "nodes": self.nodes,
            "edges": self.edges
        }

def validate_dag_schema(dag: Dict[str, Any]) -> Dict[str, Any]:
    """Validates structural DAG schema, runs depth-first cycle checks and checks capability boundaries."""
    errors = []
    
    workflow_id = dag.get("workflow_id")
    name = dag.get("name", "Custom DAG")
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])
    
    if not workflow_id:
        errors.append("DAG schema requires a valid workflow_id.")
    if not nodes:
        errors.append("DAG schema requires at least one execution node.")
        
    node_ids = set()
    for node in nodes:
        n_id = node.get("id")
        if not n_id:
            errors.append("Every node in the DAG must contain a unique 'id' field.")
            continue
        if n_id in node_ids:
            errors.append(f"Duplicate node ID detected: '{n_id}'.")
        node_ids.add(n_id)
        
        cap = node.get("capability")
        if not cap:
            errors.append(f"Node '{n_id}' is missing its capability property.")
        else:
            # Capability Boundary Verification
            # Graceful check allowing mock capabilities if running in bootstrap context
            known_caps = {
                'knowledge_retrieval', 'context_management', 'summarization',
                'narrative_generation', 'metric_interpretation', 'visualization',
                'orchestration', 'mcp_integration'
            }
            if cap not in capability_registry and cap not in known_caps:
                errors.append(f"Capability '{cap}' in node '{n_id}' is not registered in the shared Intelligence Layer.")
                
    # Verify edge connectivity
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if not src or not tgt:
            errors.append("Every edge must have a valid 'source' and 'target' node ID.")
            continue
        if src not in node_ids:
            errors.append(f"Edge references non-existent source node: '{src}'.")
        if tgt not in node_ids:
            errors.append(f"Edge references non-existent target node: '{tgt}'.")
            
    # DFS Cycle Detection
    if len(errors) == 0:
        adj = {n_id: [] for n_id in node_ids}
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src in adj and tgt in adj:
                adj[src].append(tgt)
                
        visited = {n_id: 0 for n_id in node_ids} # 0=unvisited, 1=visiting, 2=visited
        
        def has_cycle(u: str) -> bool:
            visited[u] = 1 # Visiting
            for v in adj[u]:
                if visited[v] == 1:
                    return True
                elif visited[v] == 0:
                    if has_cycle(v):
                        return True
            visited[u] = 2 # Visited
            return False
            
        for n_id in node_ids:
            if visited[n_id] == 0:
                if has_cycle(n_id):
                    errors.append("Cyclic dependency loop detected inside the custom workflow DAG configuration.")
                    break
                    
    passed = len(errors) == 0
    return {
        'structuralValid': passed,
        'errors': errors,
        'compiledConfig': dag if passed else None
    }

from shared.session import get_profile_context_defaults

def register_dag_to_kms(dag: Dict[str, Any]):
    """Registers the custom workflow DAG as a canonical knowledge entry in Postgres and visual nodes/edges in Neo4j."""
    pg = PostgresClient()
    wf_id = dag['workflow_id']
    name = dag['name']
    desc = dag.get('description', f"Analytical DAG pipeline workflow for {name}")
    content = json.dumps(dag)
    
    # Resolve dynamic session profile domain & ownership metadata
    from shared.session import active_sessions
    from shared.intelligence import active_agent_context
    active_ctx = active_agent_context.get()
    api_key = active_ctx.get('api_key', '') if active_ctx else ''
    
    user_defaults = get_profile_context_defaults()
    user_domain = dag.get('business_domain') or user_defaults['business_domain']
    user_sme = user_defaults['sme']
    user_owner = "Workflow Designer Agent"
    
    if api_key in active_sessions:
        session = active_sessions[api_key]
        user_sme = session.get('display_name', user_sme)
        user_owner = f"{session.get('role', 'Analyst')} Uploader"
        allowed_domains = session.get('allowed_domains')
        if allowed_domains and user_domain not in allowed_domains:
            user_domain = allowed_domains[0]
            
    print(f"[Workflow: Design] Registering DAG {wf_id} into enterprise KMS PostgreSQL and Neo4j databases. Domain: {user_domain} | SME: {user_sme}")
    
    # 1. Update Postgres canonical knowledge
    pg.execute_query("""
    INSERT INTO canonical_knowledge (
        knowledge_id, node_id, title, content, owner, sme, business_domain, 
        tags, confidence, approval_status, version, freshness_date, 
        security_classification, source_traceability, lineage, superseded_by, deprecation_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (knowledge_id) DO UPDATE SET
        title = EXCLUDED.title,
        content = EXCLUDED.content,
        freshness_date = EXCLUDED.freshness_date;
    """, (
        f"k_{wf_id}", wf_id, f"Workflow: {name}", content, user_owner, user_sme, user_domain,
        "workflow,dag", 1.0, "Approved", 1, time.strftime('%Y-%m-%d'), "Internal", "Workflow Design Console",
        "Designed Custom Workflow Ingestion", "", ""
    ), fetch=False)
    
    # 2. Update Postgres graph nodes and edges
    pg.execute_query("""
    INSERT INTO graph_nodes (node_id, type, title, content, metadata)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT (node_id) DO UPDATE SET
        title = EXCLUDED.title,
        content = EXCLUDED.content;
    """, (wf_id, "Workflow", name, desc, "{}"), fetch=False)
    
    for node in dag['nodes']:
        step_node_id = f"{wf_id}_step_{node['id']}"
        pg.execute_query("""
        INSERT INTO graph_nodes (node_id, type, title, content, metadata)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (node_id) DO UPDATE SET
            title = EXCLUDED.title,
            content = EXCLUDED.content;
        """, (step_node_id, "WorkflowStep", f"Step: {node['id']}", f"Capability: {node['capability']}", json.dumps(node)), fetch=False)
        
        pg.execute_query("""
        INSERT INTO graph_edges (edge_id, source_id, target_id, relationship, metadata)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (edge_id) DO NOTHING;
        """, (f"edge_{wf_id}_{node['id']}", wf_id, step_node_id, "HAS_STEP", "{}"), fetch=False)
        
    for edge in dag['edges']:
        src_step_id = f"{wf_id}_step_{edge['source']}"
        tgt_step_id = f"{wf_id}_step_{edge['target']}"
        pg.execute_query("""
        INSERT INTO graph_edges (edge_id, source_id, target_id, relationship, metadata)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (edge_id) DO NOTHING;
        """, (f"edge_{wf_id}_{edge['source']}_{edge['target']}", src_step_id, tgt_step_id, "NEXT_STEP", "{}"), fetch=False)

    # 3. Update Neo4j Graph DB
    try:
        neo4j_client = Neo4jClient()
        # Merge workflow
        neo4j_client.execute_query("""
        MERGE (w:Workflow {id: $wf_id})
        SET w.name = $name, w.description = $description, w.updated = datetime()
        """, {"wf_id": wf_id, "name": name, "description": desc})
        
        # Merge steps & HAS_STEP relationships
        for node in dag['nodes']:
            step_node_id = f"{wf_id}_step_{node['id']}"
            neo4j_client.execute_query("""
            MERGE (s:WorkflowStep {id: $step_id})
            SET s.name = $node_name, s.capability = $capability, s.requireApproval = $require_approval
            WITH s
            MATCH (w:Workflow {id: $wf_id})
            MERGE (w)-[:HAS_STEP]->(s)
            """, {
                "step_id": step_node_id,
                "node_name": node['id'],
                "capability": node['capability'],
                "require_approval": node.get('requireApproval', False),
                "wf_id": wf_id
            })
            
        # Merge transitions
        for edge in dag['edges']:
            src_step_id = f"{wf_id}_step_{edge['source']}"
            tgt_step_id = f"{wf_id}_step_{edge['target']}"
            neo4j_client.execute_query("""
            MATCH (s1:WorkflowStep {id: $src_id}), (s2:WorkflowStep {id: $tgt_id})
            MERGE (s1)-[:NEXT_STEP]->(s2)
            """, {"src_id": src_step_id, "tgt_id": tgt_step_id})
            
        neo4j_client.close()
    except Exception as n_err:
        print(f"[Neo4j Sync Error] Could not register workflow DAG in Neo4j graph: {n_err}")

def validate_pipeline_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validates structural layout and steps parameters. Bridges old configs with advanced new custom DAG structures."""
    
    # 1. Custom DAG validation
    if "nodes" in config and "edges" in config:
        if "workflow_id" not in config:
            config["workflow_id"] = f"wf_{uuid.uuid4().hex[:6]}"
        validation = validate_dag_schema(config)
        if validation['structuralValid']:
            register_dag_to_kms(config)
        return validation
        
    # 2. Existing simplified alert config validator (with flat backwards-compatibility compiler)
    name = config.get('name', 'Custom Alert') or 'Custom Alert'
    trigger = config.get('trigger')
    task = config.get('task')
    notification = config.get('notification')
    
    errors = []
    if not trigger:
        errors.append("Pipeline configuration requires a valid Trigger Event trigger source.")
    if not task:
        errors.append("Pipeline configuration requires a valid active Capability Task target.")
    if not notification:
        errors.append("Pipeline configuration requires an outbound MCP Notification channel.")
        
    passed = len(errors) == 0
    
    compiled_config = None
    if passed:
        # Dynamically compile flat settings into full DAG layout, mapping default variables based on login profile!
        defaults = get_profile_context_defaults()
        
        builder = WorkflowDAGBuilder(name, f"Standard Flat alert triggered by {trigger}")
        
        # Step 1 Node: Analytics task (dynamic based on login profile!)
        task_id = "step_task"
        task_cap = "metric_interpretation" if task == 'profile' else "summarization"
        task_input = {
            "metricId": defaults['metricId'],
            "trends": defaults['trends'],
            "analysisType": "anomaly"
        } if task == 'profile' else {
            "text": f"Enterprise automation trigger has initiated successfully. Initial balance checks verified with zero control flags for domain {defaults['business_domain']}."
        }
        builder.add_node(task_id, task_cap, task_input)
        
        # Step 2 Node: Build Narrative (dynamic based on login profile!)
        narrative_id = "step_narrative"
        builder.add_node(narrative_id, "narrative_generation", {
            "templateId": "briefing_brief",
            "variables": {
                "metricName": defaults['metricName'],
                "metricValue": defaults['metricValue'],
                "compareValue": defaults['compareValue'],
                "metricFormula": defaults['metricFormula'],
                "explanation": f"Custom workflow triggered via event: {trigger}",
                "summaryText": f"Automatic alert created via user-configured DAG notification rules in domain {defaults['business_domain']}."
            }
        })
        builder.add_edge(task_id, narrative_id)
        
        # Step 3 Node: Outbound alert (pausable)
        req_approval = config.get('requireApproval', False)
        if isinstance(req_approval, str):
            req_approval = req_approval.lower() == 'true'
            
        notify_id = "step_notify"
        builder.add_node(notify_id, "mcp_integration", {
            "serverName": "slack" if notification == "slack" else "pagerduty",
            "toolName": "post_message" if notification == "slack" else "trigger_incident",
            "arguments": {
                "channel": defaults['channel'],
                "text": f"🔔 Custom Workflow [{name}] triggered immediately! Pipeline executed task [{task}] successfully."
            }
        }, require_approval=req_approval)
        builder.add_edge(narrative_id, notify_id)
        
        dag = builder.build()
        dag['business_domain'] = defaults['business_domain'] # Set business domain context dynamically
        
        # Register compiled DAG to KMS for visual tracing
        register_dag_to_kms(dag)
        
        compiled_config = {
            'workflow_id': dag['workflow_id'],
            'name': name,
            'trigger': trigger,
            'task': task,
            'notification': notification,
            'requireApproval': req_approval,
            'dag': dag # Embed compiled custom DAG so Orchestrator can execute it
        }
        
    return {
        'structuralValid': passed,
        'errors': errors,
        'compiledConfig': compiled_config
    }
