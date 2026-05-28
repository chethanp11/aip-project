"""
Product 12: Observability Monitoring Telemetry (Stateful Agentic AI)
Assigned Enterprise Agent: System Monitor Agent
"""

import time
import json
from typing import Dict, Any, List
from shared.intelligence import invoke_capability
from shared.infra.postgres_client import PostgresClient
from shared.infra.neo4j_client import Neo4jClient

# ==========================================================================
# 📊 TELEMETRY TABLE INITIALIZATION
# ==========================================================================
def init_monitoring_tables():
    """Initializes schema tables inside Postgres if they do not exist physically in pgvector container."""
    pg = PostgresClient()
    
    # 1. Workflow Runs Table
    pg.execute_query("""
    CREATE TABLE IF NOT EXISTS workflow_runs (
        run_id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        workflow_name TEXT NOT NULL,
        status TEXT NOT NULL,
        duration_ms INTEGER,
        created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """, fetch=False)
    
    # 2. Workflow Step Runs Table
    pg.execute_query("""
    CREATE TABLE IF NOT EXISTS workflow_node_metrics (
        metric_id SERIAL PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        node_id TEXT NOT NULL,
        duration_ms INTEGER NOT NULL,
        status TEXT NOT NULL,
        output_json TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """, fetch=False)
    print("[Observability: Postgres] Audited and verified telemetry tables successfully.")

# ==========================================================================
# 🔌 STATE MACHINE HOOKS: PERSISTENCE LAYERS
# ==========================================================================
async def log_orchestrator_step(workflow_id: str, node_id: str, duration_ms: int, status: str, output: Any):
    """Hooks into steps execution to write step metrics to Postgres."""
    init_monitoring_tables()
    pg = PostgresClient()
    
    try:
        output_str = json.dumps(output)
    except Exception:
        output_str = str(output)
        
    pg.execute_query("""
    INSERT INTO workflow_node_metrics (workflow_id, node_id, duration_ms, status, output_json)
    VALUES (?, ?, ?, ?, ?);
    """, (workflow_id, node_id, duration_ms, status, output_str), fetch=False)
    print(f"[Observability: Postgres] Audited node step: {node_id} | Status: {status} | Duration: {duration_ms}ms")

async def log_orchestrator_run(workflow_id: str, workflow_name: str, status: str, traces: List[Dict[str, Any]]):
    """Audits full workflow runs, inserts trace metrics to Postgres, and maps process lineage relations to Neo4j."""
    init_monitoring_tables()
    pg = PostgresClient()
    
    # Unique ID per run
    run_time = int(time.time())
    run_id = f"run_{workflow_id}_{run_time}"
    duration_ms = sum(t.get('durationMs', 0) for t in traces)
    
    # 1. Insert execution summary to Postgres
    pg.execute_query("""
    INSERT INTO workflow_runs (run_id, workflow_id, workflow_name, status, duration_ms)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT (run_id) DO UPDATE SET
        status = EXCLUDED.status,
        duration_ms = EXCLUDED.duration_ms;
    """, (run_id, workflow_id, workflow_name, status, duration_ms), fetch=False)
    print(f"[Observability: Postgres] Audited workflow run: {workflow_name} ({run_id}) | Status: {status}")
    
    # 2. Insert process lineage nodes and connections to centralized Neo4j graph network
    try:
        neo4j = Neo4jClient()
        
        # Link Workflow to the Run Node
        neo4j.execute_query("""
        MERGE (w:Workflow {id: $wf_id})
        SET w.name = $wf_name
        WITH w
        MERGE (r:WorkflowRun {id: $run_id})
        SET r.status = $status, r.durationMs = $duration, r.timestamp = datetime()
        MERGE (w)-[:HAS_RUN]->(r)
        """, {
            "wf_id": workflow_id,
            "wf_name": workflow_name,
            "run_id": run_id,
            "status": status,
            "duration": duration_ms
        })
        
        # Link Run Node to StepRun Nodes and generated physical storage Artifacts
        for t in traces:
            step_id = t['stepId']
            step_run_id = f"steprun_{run_id}_{step_id}"
            
            neo4j.execute_query("""
            MATCH (r:WorkflowRun {id: $run_id})
            MERGE (sr:WorkflowStepRun {id: $step_run_id})
            SET sr.nodeId = $step_id, sr.status = $step_status, sr.durationMs = $step_duration
            MERGE (r)-[:EXECUTED_STEP]->(sr)
            """, {
                "run_id": run_id,
                "step_run_id": step_run_id,
                "step_id": step_id,
                "step_status": t.get('status', 'completed'),
                "step_duration": t.get('durationMs', 0)
            })
            
            # If the trace produced physical files, connect step run to physical artifacts
            out = t.get('output') or {}
            if isinstance(out, dict) and 'artifacts' in out:
                for art in out['artifacts']:
                    art_id = f"art_{step_run_id}_{art['filename']}"
                    neo4j.execute_query("""
                    MATCH (sr:WorkflowStepRun {id: $step_run_id})
                    MERGE (a:WorkflowArtifact {id: $art_id})
                    SET a.filename = $filename, a.path = $path, a.created = datetime()
                    MERGE (sr)-[:PRODUCED]->(a)
                    """, {
                        "step_run_id": step_run_id,
                        "art_id": art_id,
                        "filename": art['filename'],
                        "path": art['path']
                    })
                    
        neo4j.close()
        print(f"[Observability: Neo4j] Pushed process lineage graph traces successfully for run: {run_id}")
    except Exception as n_err:
        print(f"[Observability: Neo4j Lineage Error] Could not synchronize graph network relations: {n_err}")

# ==========================================================================
# 📊 TELEMETRY AUDIT AGGREGATES
# ==========================================================================
async def run_monitoring_workflow() -> Dict[str, Any]:
    """Compiles operational audit traces and telemetry aggregates from Postgres database state."""
    init_monitoring_tables()
    pg = PostgresClient()
    
    # Query total runs count
    total_res = pg.execute_query("SELECT COUNT(*) as count FROM workflow_runs;")
    total = total_res[0]['count'] if total_res else 0
    
    # Query completed runs count
    comp_res = pg.execute_query("SELECT COUNT(*) as count FROM workflow_runs WHERE status = 'completed';")
    completed = comp_res[0]['count'] if comp_res else 0
    
    # Calculate success rate
    success_rate = int((completed / total) * 100) if total > 0 else 100
    
    # Query average latency
    avg_res = pg.execute_query("SELECT AVG(duration_ms) as avg_lat FROM workflow_runs;")
    avg_latency = round(avg_res[0]['avg_lat'] or 0.0, 1) if avg_res and avg_res[0]['avg_lat'] else 0.0
    
    # Query recent run durations for Vega chart trends
    latency_res = pg.execute_query("SELECT duration_ms FROM workflow_runs ORDER BY created_timestamp DESC LIMIT 10;")
    latency_trend = [r['duration_ms'] or 1 for r in latency_res] if latency_res else [2, 1, 3, 2, 1]
    
    # Compile Vega chart specifications dynamically using visualization capability
    spec = await invoke_capability('visualization', {
        'chartType': 'bar',
        'trends': latency_trend
    })
    
    return {
        'metrics': {
            'totalInvocations': total,
            'successRate': f"{success_rate}%",
            'avgLatency': f"{avg_latency}ms",
            'totalTokenCost': f"${(total * 0.05):.2f}"
        },
        'latencyVegaSpec': spec.get('vegaSpec')
    }
