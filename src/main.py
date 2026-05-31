"""
FastAPI Server Gateway Entrypoint (Python)
AIM Intelligence Platform (AIP)
"""

import os
import sys

# Ensure workspace root and src/ are in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import random
import string
import time
from typing import Dict, Any, List
import uvicorn
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.shared.config import config
import uuid
import json
from datetime import datetime, timezone
from src.shared.infra_client.storage_client import StorageClient

_storage_client = StorageClient()

class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False

    def file_response(self, *args, **kwargs) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# Import intelligence operating layer
from shared.intelligence import (
    register_capability,
    invoke_capability,
    list_capabilities,
    get_logs,
    clear_logs,
    active_agent_context
)

# Import stateless capabilities
import shared.capabilities.knowledge_retrieval as knowledge_retrieval_cap
import shared.capabilities.context_management as context_management_cap
import shared.capabilities.summarization as summarization_cap
import shared.capabilities.narrative_generation as narrative_generation_cap
import shared.capabilities.metric_interpretation as metric_interpretation_cap
import shared.capabilities.visualization as visualization_cap
import shared.capabilities.orchestration as orchestration_cap
import shared.capabilities.mcp_integration as mcp_integration_cap

# Import stateful enterprise suite agent workflows
from src.analyst_actions.prism.main import run_prism_workflow
from src.analyst_actions.research.main import run_research_workflow
from src.analyst_actions.build_report.main import (
    run_report_builder_workflow,
    initiate_report_build,
    advance_workflow_step,
    list_published_reports
)
from src.business_suite.conversational_bi.main import run_conversational_bi_workflow
from src.business_suite.proactive_alerts.main import run_proactive_insights_workflow

from src.business_suite.deep_insights.main import run_insight_discovery_workflow
from src.analyst_actions.root_cause_analysis.main import run_rca_workflow
from src.business_suite.scenario_analysis.main import run_whatif_workflow
from src.analyst_actions.recommend_actions.main import run_business_narratives_workflow


from src.shared.infra_client.analytics_client import AnalyticsClient

analytics_client = AnalyticsClient()
get_lms_table = analytics_client.get_table_rows


# Initialize and register all stateless capabilities
register_capability('knowledge_retrieval', knowledge_retrieval_cap.config, knowledge_retrieval_cap.handler)
register_capability('context_management', context_management_cap.config, context_management_cap.handler)
register_capability('summarization', summarization_cap.config, summarization_cap.handler)
register_capability('narrative_generation', narrative_generation_cap.config, narrative_generation_cap.handler)
register_capability('metric_interpretation', metric_interpretation_cap.config, metric_interpretation_cap.handler)
register_capability('visualization', visualization_cap.config, visualization_cap.handler)
register_capability('orchestration', orchestration_cap.config, orchestration_cap.handler)
register_capability('mcp_integration', mcp_integration_cap.config, mcp_integration_cap.handler)

app = FastAPI(title="AIM Intelligence Platform API")

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================================
# 🔒 REQUEST-SCOPE AUTHENTICATION & THREAD-SAFE CONTEXT TRACING MIDDLEWARE
# ==========================================================================
@app.middleware("http")
async def context_and_auth_middleware(request: Request, call_next):
    path = request.url.path

    # Bypass auth verification for static UI pages and login POSTs
    if (
        request.method == "OPTIONS"
        or path == "/"
        or path.startswith("/index.")
        or path.startswith("/static")
        or path == "/api/v1/auth/login"
        or path == "/api/v1/auth/sme-login"
        or path == "/api/v1/auth/logout"
        or not path.startswith("/api/v1")
    ):
        return await call_next(request)

    # Validate Authorization Header Bearer prefix
    auth_header = request.headers.get('Authorization')
    api_key = ''
    if auth_header and auth_header.startswith('Bearer '):
        api_key = auth_header.split(' ', 1)[1]

    if not api_key or not api_key.startswith('AIP-'):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized: Missing or invalid API key. Must start with 'AIP-'"}
        )

    # Map endpoint paths to calling Agent personae (telemetry grounding)
    agent_name = "Platform Routing Agent"
    if "/dashboards/reports" in path:
        agent_name = "Report Viewer Agent"
    elif "/workflows/reporting/conversational-bi" in path:
        agent_name = "Conversational BI Agent"
    elif "/workflows/reporting/build" in path:
        agent_name = "Report Builder Agent"
    elif "/workflows/reporting/proactive" in path:
        agent_name = "Proactive Monitor Agent"
    elif "/workflows/reporting/prism-lite" in path:
        agent_name = "PRISM Agent"
    elif "/workflows/analyst/research" in path:
        agent_name = "Research Agent"
    elif "/workflows/analytics/rca" in path:
        agent_name = "RCA Diagnostic Agent"
    elif "/workflows/analytics/insight-discovery" in path:
        agent_name = "Insight Discovery Agent"
    elif "/workflows/analytics/what-if" in path:
        agent_name = "What-if Simulator Agent"
    elif "/workflows/analytics/business-narratives" in path:
        agent_name = "Narrative Storyteller Agent"

    elif "/lms/query" in path or "/knowledge" in path:
        agent_name = "Analytical Grounding Agent"
    elif "/analytics-data" in path:
        agent_name = "Data Architect Agent"


    # Set thread-safe request-scope contextvars
    token = active_agent_context.set({'agent': agent_name, 'api_key': api_key})
    try:
        response = await call_next(request)
        return response
    finally:
        active_agent_context.reset(token)

# ==========================================================================
# 🔑 CENTRAL UNIFIED LOGIN ROUTE
# ==========================================================================
@app.post("/api/v1/auth/login")
async def login(payload: Dict[str, Any]):
    username = payload.get('username')
    password = payload.get('password')
    lob = payload.get('lob')
    category = payload.get('category')

    # Authenticate any registered Analyst or SME profile
    user = authenticate_kms_user(username, password)
    if user:
        # If logging in as the general "user" account, dynamically assume LOB and Category persona
        if username == "user" and lob and category:
            # Category mappings to role and clearance
            if category == "Business User":
                user['role'] = "Business User"
                user['clearance'] = "Internal"
                user['display_name'] = f"{lob} Business User"
            elif category == "Analytics Professional":
                user['role'] = "Analyst"
                user['clearance'] = "Internal"
                user['display_name'] = f"{lob} Analyst"
            elif category == "Business Admin":
                user['role'] = "SME"
                user['clearance'] = "Confidential"
                user['display_name'] = f"{lob} SME"
            
            # LOB mapping to domains and tables
            if lob == "Treasury":
                user['allowed_domains'] = "Treasury & Capital Management,Cash Management"
                user['allowed_tables'] = "accounts,transactions,liquidity_buffers,liquidity_sweeps,sweep_executions,treasury_positions,cash_forecasts,funding_plans,collateral_positions,fx_exposures,interest_rate_swaps,investment_securities,intraday_liquidity_events,nostro_balances,repo_transactions,stress_test_scenarios"
            elif lob == "Compliance":
                user['allowed_domains'] = "Regulatory Compliance"
                user['allowed_tables'] = "corporate_clients,transactions,regulatory_obligations,compliance_controls,compliance_reviews,compliance_issues"
            elif lob == "Wealth":
                user['allowed_domains'] = "Wealth Management"
                user['allowed_tables'] = "accounts,corporate_clients,transactions,wealth_clients,investment_accounts,portfolio_holdings,advisory_mandates,financial_plans,client_risk_profiles,investment_transactions,fee_schedules,relationship_managers,client_goals"
            elif lob == "Credit":
                user['allowed_domains'] = "Credit Portfolio Risk"
                user['allowed_tables'] = "corporate_clients,accounts,transactions,credit_facilities,credit_risk_ratings,delinquency_events"

        role = user['role']
        session_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=9))
        secure_token = f"AIP-{role.upper().replace(' ', '_')}-SESSION-{session_suffix}"

        # Store user profile in active session
        allowed_domains = [d.strip() for d in (user.get('allowed_domains') or '').split(',') if d.strip()] if user.get('allowed_domains') else None
        kms_team = config.resolve_kms_team(user['username'] if username != 'user' else f"{lob}_{role}", allowed_domains)
        session_payload = {
            'username': user['username'] if username != 'user' else f"{lob}_{role}",
            'role': user['role'],
            'clearance': user['clearance'],
            'display_name': user['display_name'],
            'allowed_domains': allowed_domains,
            'allowed_tables': [t.strip().lower() for t in (user.get('allowed_tables') or '').split(',') if t.strip()] if user.get('allowed_tables') else None,
            'kms_team': kms_team,
            'kms_context_path': config.get_kms_team_path(kms_team)
        }
        from shared.session import set_session
        set_session(secure_token, session_payload)

        print(f"[Auth Success] Authenticated {role} {username}. Issued secure session token: {secure_token}")
        return {'success': True, 'token': secure_token, 'role': user['role'], 'clearance': user['clearance'], 'displayName': user['display_name']}

    raise HTTPException(
        status_code=401,
        detail="Invalid credentials."
    )

@app.post("/api/v1/auth/sme-login")
async def sme_login(payload: Dict[str, Any]):
    # Keep backwards parity, but defer to central unified login
    return await login(payload)

@app.post("/api/v1/auth/logout")
async def logout(request: Request):
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1]
        from shared.session import clear_session
        clear_session(token)
        print(f"[Auth Logout] Successfully logged out token: {token}")
        return {'success': True}
    return {'success': False, 'error': 'No active session token provided.'}

# ==========================================================================
# ⚙️ DYNAMIC UI CONFIGURATION ENDPOINTS
# ==========================================================================
@app.get("/api/v1/ui/config")
async def get_ui_config():
    """Retrieves all persona-based UI configurations from PostgreSQL."""
    try:
        from src.kms.index import get_postgres_db
        import json
        conn = get_postgres_db()
        cursor = conn.cursor()
        cursor.execute("SELECT category, visible_suites, visible_subproducts FROM ui_configurations;")
        rows = cursor.fetchall()
        
        configs = {}
        for r in rows:
            try:
                subproducts = json.loads(r['visible_subproducts'])
            except Exception:
                subproducts = {}
            configs[r['category']] = {
                "visible_suites": [s.strip() for s in r['visible_suites'].split(',') if s.strip()],
                "visible_subproducts": subproducts
            }
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error reading UI config: {str(e)}")

@app.post("/api/v1/ui/config")
async def save_ui_config(payload: Dict[str, Any], request: Request):
    """Saves/Updates persona UI configuration. Restricts access strictly to Business Admins (SME)."""
    # Verify authentication and authorization
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing authorization header.")
    
    token = auth_header.split(' ', 1)[1]
    from shared.session import active_sessions
    if token not in active_sessions:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")
        
    session = active_sessions[token]
    # Restrict to SME (Business Admin) role only!
    if session.get('role') != 'SME':
        raise HTTPException(status_code=403, detail="Forbidden: Only Business Admins (SME) can modify UI configurations.")

    category = payload.get('category')
    visible_suites = payload.get('visible_suites') # String, e.g., "home,reporting,analytics"
    visible_subproducts = payload.get('visible_subproducts') # Dict/JSON, e.g. {"reporting": ["bi"]}

    if not category or not isinstance(visible_suites, str) or not isinstance(visible_subproducts, dict):
        raise HTTPException(status_code=400, detail="Invalid payload. category, visible_suites, and visible_subproducts are required.")

    try:
        from src.kms.index import get_postgres_db
        import json
        conn = get_postgres_db()
        cursor = conn.cursor()
        
        # PostgreSQL UPSERT emulated/handled
        cursor.execute("DELETE FROM ui_configurations WHERE category = %s;", (category,))
        cursor.execute("""
            INSERT INTO ui_configurations (category, visible_suites, visible_subproducts)
            VALUES (%s, %s, %s);
        """, (category, visible_suites, json.dumps(visible_subproducts)))
        conn.commit()
        print(f"[UI Config Update] SME {session.get('username')} updated UI config for category '{category}' successfully.")
        return {"success": True, "message": f"UI Configuration for category '{category}' updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error writing UI config: {str(e)}")

# ==========================================================================
# 📊 ENTERPRISE LEDGER DATABASE ROUTE
# ==========================================================================
@app.get("/api/v1/lms/query")
async def query_lms(table: str = None):
    # Fetch allowed tables from active session
    from shared.session import active_sessions
    active_ctx = active_agent_context.get()
    api_key = active_ctx.get('api_key', '') if active_ctx else ''
    allowed_tables = None
    if api_key in active_sessions:
        allowed_tables = active_sessions[api_key].get('allowed_tables')

    if allowed_tables is not None:
        if table:
            if table.lower() not in allowed_tables:
                raise HTTPException(status_code=403, detail=f"Access Denied: User profile does not have permission to access table '{table}'.")
            records = get_lms_table(table)
            if not records:
                raise HTTPException(status_code=404, detail=f"Table '{table}' not found in Enterprise Ledger.")
            return records
        else:
            res = {}
            for t in ['deposits', 'loans', 'liquidity_buffers', 'branch_performance']:
                if t.lower() in allowed_tables:
                    res[t] = get_lms_table(t)
            return res
    else:
        if table:
            records = get_lms_table(table)
            if not records:
                raise HTTPException(status_code=404, detail=f"Table '{table}' not found in Enterprise Ledger.")
            return records
        else:
            return {
                'deposits': get_lms_table('deposits'),
                'loans': get_lms_table('loans'),
                'liquidity_buffers': get_lms_table('liquidity_buffers'),
                'branch_performance': get_lms_table('branch_performance')
            }

# ==========================================================================
# 🗄️ ANALYTICS SOURCE DATABASE ROUTES
# ==========================================================================
@app.get("/api/v1/analytics-data/tables")
async def list_source_tables():
    try:
        return analytics_client.list_tables()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics-data/tables/{table_name}/schema")
async def get_source_table_schema(table_name: str):
    try:
        return analytics_client.get_table_schema(table_name)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/analytics-data/query")
async def query_source_database(payload: Dict[str, Any]):
    mode = payload.get("mode", "visual")
    try:
        if mode == "visual":
            table_name = payload.get("tableName")
            filters = payload.get("filters", [])
            limit = payload.get("limit", 100)
            if not table_name:
                raise HTTPException(status_code=400, detail="Missing parameter: tableName")
            return analytics_client.query_table(table_name, filters, limit)
        else:
            sql_query = payload.get("sqlQuery")
            if not sql_query:
                raise HTTPException(status_code=400, detail="Missing parameter: sqlQuery")
            return analytics_client.run_custom_query(sql_query)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================================
# 📚 KMS KNOWLEDGE ROUTES (SQLite Vector & Graph DB)
# ==========================================================================
from src.kms.index import (
    ingest_custom_file_to_kms,
    search_kms_vector_and_graph,
    list_canonical_knowledge,
    approve_canonical_knowledge,
    rollback_knowledge_version,
    get_kms_observability_data,
    generate_context_package,
    advanced_retrieval_orchestration,
    list_source_connectors,
    list_candidate_knowledge,
    update_candidate_details,
    act_on_candidate_knowledge,
    sync_source_connector,
    generate_context_zip,
    get_business_domains_list,
    get_kms_filter_options,
    authenticate_kms_user
)


@app.get("/api/v1/kms/domains")
async def kms_business_domains_list():
    try:
        return get_business_domains_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/kms/options")
async def kms_options_list():
    try:
        return get_kms_filter_options()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/knowledge/search")
async def knowledge_search(q: str = ''):
    return await invoke_capability('knowledge_retrieval', {'question': q})

@app.get("/api/v1/knowledge/context")
async def knowledge_context(q: str = ''):
    res = await invoke_capability('knowledge_retrieval', {'question': q})
    return {'context': res.get('context', '')}

@app.post("/api/v1/kms/upload")
async def kms_upload_document(payload: Dict[str, Any]):
    filename = payload.get('filename', 'custom_regulation.txt')
    content = payload.get('content', '')
    owner = payload.get('owner', 'System Ingestion')
    security_class = payload.get('securityClassification', 'Internal')
    sme = payload.get('sme', 'Marcus Vance')
    domain = payload.get('businessDomain', 'Enterprise Analytics')
    prompt = payload.get('prompt', '')
    if not content:
        raise HTTPException(status_code=400, detail="Document content cannot be empty.")
    try:
        return await ingest_custom_file_to_kms(filename, content, owner, security_class, sme, domain, prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/query")
async def kms_query_grounding(payload: Dict[str, Any]):
    query = payload.get('query', '')
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
    try:
        res = search_kms_vector_and_graph(query)
        return {
            'groundedContext': res['context'],
            'matchedNodes': res['matched_nodes'],
            'matchedChunks': res['matched_chunks']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/kms/connectors")
async def kms_connectors_list():
    try:
        return list_source_connectors()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/connectors")
async def kms_connectors_create(payload: Dict[str, Any]):
    import uuid
    name = payload.get('name')
    type = payload.get('type')
    auth = payload.get('authPlaceholder')
    sync_method = payload.get('syncMethod', 'Manual')
    owner = payload.get('owner')
    domain = payload.get('domain')
    if not name or not type:
        raise HTTPException(status_code=400, detail="Missing name or type parameter.")
    try:
        from src.kms.index import get_kms_db
        conn = get_kms_db()
        cursor = conn.cursor()
        connector_id = "conn_" + uuid.uuid4().hex[:6]
        cursor.execute("""
            INSERT INTO source_connectors (connector_id, name, type, auth_placeholder, sync_method, owner, domain, status, error_logs, ingestion_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (connector_id, name, type, auth, sync_method, owner, domain, 'Active', '', 'Established Connection'))
        conn.commit()
        return {'success': True, 'connectorId': connector_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/connectors/sync")
async def kms_connectors_sync(payload: Dict[str, Any]):
    connector_id = payload.get('connectorId')
    if not connector_id:
        raise HTTPException(status_code=400, detail="Missing connectorId parameter.")
    try:
        return await sync_source_connector(connector_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/kms/candidates")
async def kms_candidates_list():
    try:
        return list_candidate_knowledge()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/candidates/edit")
async def kms_candidates_edit(payload: Dict[str, Any]):
    candidate_id = payload.get('candidateId')
    title = payload.get('title')
    summary = payload.get('summary')
    domain = payload.get('domain')
    tags = payload.get('tags')
    relationships = payload.get('relationships')
    if not candidate_id:
        raise HTTPException(status_code=400, detail="Missing candidateId parameter.")
    try:
        return update_candidate_details(candidate_id, title, summary, domain, tags, relationships)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/candidates/action")
async def kms_candidates_action(payload: Dict[str, Any]):
    candidate_id = payload.get('candidateId')
    status = payload.get('status')
    comments = payload.get('comments', '')
    if not candidate_id or not status:
        raise HTTPException(status_code=400, detail="Missing candidateId or status parameters.")
    try:
        return act_on_candidate_knowledge(candidate_id, status, comments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/kms/canonical")
async def kms_canonical_list():
    try:
        return list_canonical_knowledge()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/approve")
async def kms_approve_knowledge(payload: Dict[str, Any]):
    knowledge_id = payload.get('knowledgeId')
    approved = payload.get('approved', False)
    if not knowledge_id:
        raise HTTPException(status_code=400, detail="Missing knowledgeId parameter.")
    try:
        return approve_canonical_knowledge(knowledge_id, approved)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/rollback")
async def kms_rollback_knowledge(payload: Dict[str, Any]):
    knowledge_id = payload.get('knowledgeId')
    if not knowledge_id:
        raise HTTPException(status_code=400, detail="Missing knowledgeId parameter.")
    try:
        return rollback_knowledge_version(knowledge_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/kms/observability")
async def kms_observability_metrics():
    try:
        return get_kms_observability_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/context-package")
async def kms_context_package(payload: Dict[str, Any]):
    query = payload.get('query', '')
    user_role = payload.get('userRole', 'Analyst')
    clearance = payload.get('clearance', 'Internal')
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
    try:
        return generate_context_package(query, user_role, clearance)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/query-advanced")
async def kms_query_advanced(payload: Dict[str, Any]):
    query = payload.get('query', '')
    user_role = payload.get('userRole', 'Analyst')
    clearance = payload.get('clearance', 'Internal')
    limit = payload.get('limit', 4)
    search_mode = payload.get('searchMode', 'Hybrid')
    filters = payload.get('filters', {})
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
    try:
        res = advanced_retrieval_orchestration(query, user_role, clearance, limit, search_mode, filters)
        return {
            'groundedContext': res['context'],
            'matchedNodes': res['matched_nodes'],
            'matchedChunks': res['matched_chunks'],
            'agentTraces': res['agent_traces'],
            'contradictions': res['contradictions'],
            'missingContext': res['missing_context'],
            'latencyMs': res['latency_ms']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kms/retriever/download")
async def kms_retriever_download(payload: Dict[str, Any]):
    query = payload.get('query', '')
    user_role = payload.get('userRole', 'Analyst')
    clearance = payload.get('clearance', 'Internal')
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
    try:
        res = advanced_retrieval_orchestration(query, user_role, clearance)
        pkg = generate_context_package(query, user_role, clearance)
        zip_data = generate_context_zip(query, res, pkg)

        from fastapi.responses import Response
        import urllib.parse
        safe_filename = urllib.parse.quote(f"context_pack_{query[:15].replace(' ', '_')}.zip")
        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={safe_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================================================
# ⚙️ CAPABILITY REGISTRY & AUDIT TRAILS ROUTES
# ==========================================================================
@app.get("/api/v1/capabilities")
async def capabilities_list():
    return list_capabilities()

@app.post("/api/v1/capabilities/invoke")
async def capability_invoke(payload: Dict[str, Any]):
    name = payload.get('name')
    inputs = payload.get('input', {})
    try:
        output = await invoke_capability(name, inputs)
        return {'success': True, 'output': output}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/execution-logs")
async def execution_logs_get():
    return get_logs()

@app.delete("/api/v1/execution-logs")
async def execution_logs_clear():
    clear_logs()
    return {'success': True}


@app.post("/api/v1/workflows/analyst/research")
async def analyst_research(payload: Dict[str, Any]):
    query = payload.get('query', '')
    return await run_research_workflow(query)

# ==========================================================================
# 📰 REPORTING SUITE ROUTES
# ==========================================================================
@app.post("/api/v1/workflows/reporting/prism-lite")
async def prism_lite(payload: Dict[str, Any]):
    reports = payload.get('reports', [])
    prompt = payload.get('prompt', '')
    threshold = payload.get('threshold', 0.5)
    return await run_prism_workflow(reports, prompt, threshold)

@app.post("/api/v1/workflows/reporting/prism/upload")
async def upload_reports_for_screening(
    files: List[UploadFile] = File([]),
    prompt: str = ""
):
    from src.analyst_actions.prism.main import parse_excel_report, parse_html_report

    reports = []
    for file in files:
        if not isinstance(file, UploadFile):
            continue
        filename = file.filename
        content_bytes = await file.read()

        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            excel_reports = parse_excel_report(content_bytes, filename)
            reports.extend(excel_reports)
        elif filename.endswith('.html') or filename.endswith('.htm'):
            html_str = content_bytes.decode('utf-8', errors='ignore')
            html_rep = parse_html_report(html_str, filename)
            reports.append(html_rep)
        elif filename.endswith('.csv'):
            csv_str = content_bytes.decode('utf-8', errors='ignore')
            headers = [h.strip() for h in csv_str.split('\n')[0].split(',')]
            reports.append({
                'name': filename.split('.')[0],
                'query': f"SELECT {', '.join(headers[:4])} FROM {filename.split('.')[0].lower()}",
                'columns': headers,
                'usage': 10,
                'owner': 'Operations Analytics',
                'type': 'CSV'
            })

    if not reports:
        raise HTTPException(status_code=400, detail="No valid Excel, HTML, or CSV files were parsed.")

    return await run_prism_workflow(reports, prompt)


@app.post("/api/v1/workflows/reporting/build")
async def build_report(payload: Dict[str, Any]):
    metric_id = payload.get('metricId')
    val = payload.get('value')
    comp = payload.get('compareValue')
    note = payload.get('note', '')
    return await run_report_builder_workflow(metric_id, val, comp, note)

@app.post("/api/v1/workflows/reporting/build/initiate")
async def build_report_initiate(payload: Dict[str, Any]):
    mode = payload.get('mode', 'create')
    report_id = payload.get('reportId')
    requirements = payload.get('requirements', '')
    context = payload.get('context', '')
    try:
        return await initiate_report_build(mode, report_id, requirements, context)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/workflows/reporting/build/step")
async def build_report_step(payload: Dict[str, Any]):
    session_id = payload.get('sessionId')
    step = payload.get('step', 1)
    approved = payload.get('approved', False)
    feedback = payload.get('feedback', '')
    try:
        return await advance_workflow_step(session_id, step, approved, feedback)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/workflows/reporting/build/reports")
async def build_report_list():
    try:
        return list_published_reports()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workflows/reporting/conversational-bi/sessions")
async def list_conversational_bi_sessions():
    try:
        chats_dir = _storage_client.get_chats_dir()
        sessions = []
        if os.path.exists(chats_dir):
            for fname in os.listdir(chats_dir):
                if fname.startswith("session_") and fname.endswith(".json"):
                    fpath = os.path.join(chats_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            sessions.append({
                                "sessionId": data.get("sessionId"),
                                "title": data.get("title", "BI Discussion"),
                                "timestamp": data.get("timestamp", "")
                            })
                    except Exception:
                        pass
        # Sort sessions descending by timestamp
        sessions.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workflows/reporting/conversational-bi/sessions/{sessionId}")
async def get_conversational_bi_session(sessionId: str):
    try:
        chats_dir = _storage_client.get_chats_dir()
        fpath = os.path.join(chats_dir, f"session_{sessionId}.json")
        if not os.path.exists(fpath):
            raise HTTPException(status_code=404, detail="Session not found")
        
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/workflows/reporting/conversational-bi")
async def conversational_bi(payload: Dict[str, Any]):
    question = payload.get('question', '')
    session_id = payload.get('sessionId')
    
    # Run the standard visual decisioning conversational workflow
    res = await run_conversational_bi_workflow(question)
    
    try:
        chats_dir = _storage_client.get_chats_dir()
        if not session_id:
            session_id = str(uuid.uuid4())
            
        fpath = os.path.join(chats_dir, f"session_{session_id}.json")
        
        session_data = {
            "sessionId": session_id,
            "title": "BI Discussion",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "messages": []
        }
        
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        session_data = loaded
            except Exception:
                pass
                
        # Append User Message
        user_msg = {
            "role": "user",
            "content": question,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        
        # Append Bot Message
        bot_msg = {
            "role": "bot",
            "content": res.get("narrative", ""),
            "renderedHtml": res.get("renderedHtml", ""),
            "visualDecision": res.get("visualDecision"),
            "vegaSpec": res.get("vegaSpec"),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        
        if "messages" not in session_data or not isinstance(session_data["messages"], list):
            session_data["messages"] = []
            
        session_data["messages"].append(user_msg)
        session_data["messages"].append(bot_msg)
        
        # Set title from first question if it was empty/default
        if session_data.get("title") in (None, "BI Discussion", "") and session_data["messages"]:
            first_q = session_data["messages"][0]["content"]
            session_data["title"] = first_q[:45] + "..." if len(first_q) > 45 else first_q
            
        session_data["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Save session file
        _storage_client.save_file(chats_dir, f"session_{session_id}.json", json.dumps(session_data, indent=2))
        
        # Add metadata to response for frontend client
        res["sessionId"] = session_id
        res["sessionTitle"] = session_data["title"]
        
    except Exception as exc:
        print(f"[Gateway API] Error saving chat session: {str(exc)}")
        
    return res

@app.get("/api/v1/workflows/reporting/proactive-insights")
async def proactive_insights():
    return await run_proactive_insights_workflow()

@app.get("/api/v1/workflows/reporting/proactive-insights/rules")
async def get_proactive_alert_rules():
    import os
    import json
    from src.shared.config.config import ALERTS_PATH
    
    rules_file = os.path.join(ALERTS_PATH, "rules.json")
    if not os.path.exists(rules_file):
        # Seed default rules
        default_rules = [
            {"id": "rule_1", "rule": "Notify if Net Interest Margin (NIM) drops below 3.6%"},
            {"id": "rule_2", "rule": "Alert if liquidity coverage ratio (LCR) falls below 110%"},
            {"id": "rule_3", "rule": "Alert if Population Stability Index (PSI) exceeds 0.2"}
        ]
        os.makedirs(ALERTS_PATH, exist_ok=True)
        with open(rules_file, "w", encoding="utf-8") as f:
            json.dump(default_rules, f, indent=2)
        return default_rules
        
    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read rules: {str(e)}")

@app.post("/api/v1/workflows/reporting/proactive-insights/rules")
async def create_proactive_alert_rule(payload: Dict[str, Any]):
    import os
    import json
    import uuid
    from src.shared.config.config import ALERTS_PATH
    
    rule_text = payload.get("rule", "").strip()
    if not rule_text:
        raise HTTPException(status_code=400, detail="Rule text cannot be empty.")
        
    rules_file = os.path.join(ALERTS_PATH, "rules.json")
    rules = []
    if os.path.exists(rules_file):
        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                rules = json.load(f)
        except Exception:
            rules = []
            
    new_rule = {
        "id": f"rule_{uuid.uuid4().hex[:6]}",
        "rule": rule_text
    }
    rules.append(new_rule)
    
    try:
        os.makedirs(ALERTS_PATH, exist_ok=True)
        with open(rules_file, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2)
        return {"success": True, "rule": new_rule}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save rule: {str(e)}")

@app.delete("/api/v1/workflows/reporting/proactive-insights/rules/{rule_id}")
async def delete_proactive_alert_rule(rule_id: str):
    import os
    import json
    from src.shared.config.config import ALERTS_PATH
    
    rules_file = os.path.join(ALERTS_PATH, "rules.json")
    if not os.path.exists(rules_file):
        raise HTTPException(status_code=404, detail="No rules found.")
        
    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            rules = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read rules: {str(e)}")
        
    filtered_rules = [r for r in rules if r.get("id") != rule_id]
    if len(filtered_rules) == len(rules):
        raise HTTPException(status_code=404, detail="Rule not found.")
        
    try:
        with open(rules_file, "w", encoding="utf-8") as f:
            json.dump(filtered_rules, f, indent=2)
        return {"success": True, "message": "Rule deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")

# ==========================================================================
# 📈 BUSINESS ANALYTICS SUITE ROUTES
# ==========================================================================
@app.post("/api/v1/workflows/analytics/insight-discovery")
async def insight_discovery(payload: Dict[str, Any]):
    segments = payload.get('segmentsData', [])
    return await run_insight_discovery_workflow(segments)

@app.post("/api/v1/workflows/analytics/rca")
async def rca(payload: Dict[str, Any]):
    dataset = payload.get('datasetName', '')
    metrics = payload.get('metricsData', [])
    prompt = payload.get('prompt', '')
    return await run_rca_workflow(dataset, metrics, prompt)

@app.post("/api/v1/workflows/analytics/what-if")
async def what_if(payload: Dict[str, Any]):
    earning_rate = payload.get('earningRate', payload.get('loanRate'))
    resource_cost_rate = payload.get('resourceCostRate', payload.get('depositRate'))
    assets = payload.get('assets')
    npl_rate = payload.get('nplRate')
    return run_whatif_workflow(earning_rate, resource_cost_rate, assets, npl_rate)

@app.post("/api/v1/workflows/analytics/business-narratives")
async def narratives(payload: Dict[str, Any]):
    channel = payload.get('channel', 'slack')
    metric = payload.get('metricName', 'NIM Compression')
    val = payload.get('value', '3.60')
    growth = payload.get('growthRate', '0.0')
    driver = payload.get('primaryDriver', 'Retail Loans')
    prompt = payload.get('prompt', '')
    return await run_business_narratives_workflow(channel, metric, val, growth, driver, prompt)


# ==========================================================================
# 📊 BUSINESS SUITE DASHBOARD VIEW ENDPOINTS
# ==========================================================================
@app.get("/api/v1/dashboards/reports")
async def list_dashboard_reports():
    from src.business_suite.dashboards.main import get_dashboard_reports
    return get_dashboard_reports()

@app.get("/api/v1/dashboards/reports/{filename}")
async def get_dashboard_report(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.endswith(".html"):
        raise HTTPException(status_code=400, detail="Only HTML files are allowed")
    
    file_path = os.path.join(config.SHARED_REPORT_PATH, filename)
    if not os.path.exists(file_path):
        file_path = os.path.join(config.REPORT_PATH, filename)
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    return FileResponse(file_path, media_type="text/html")

# ==========================================================================
# 🌐 MOUNT STATIC FRONTEND PLATFORM CLIENT SHELL & MICRO-FRONTENDS
# ==========================================================================
# 1. Mount published HTML report briefing folder at "/reports"
from src.shared.config import config
reports_dir = config.REPORT_PATH
os.makedirs(reports_dir, exist_ok=True)
app.mount("/reports", NoCacheStaticFiles(directory=reports_dir, html=True), name="reports_pub")

# 1a. Seed premium reports if empty
from src.business_suite.dashboards.main import seed_premium_reports_if_empty
try:
    seed_premium_reports_if_empty()
except Exception as e:
    print(f"Error seeding premium reports: {e}")

# 2. Mount micro-frontend static product UIs dynamically
sub_apps_paths = [
    ("/ui/kms", "src/kms/ui"),
    ("/ui/reporting/prism", "src/analyst_actions/prism/ui"),
    ("/ui/analyst_actions/prism", "src/analyst_actions/prism/ui"),
    ("/ui/analyst_actions/research", "src/analyst_actions/research/ui"),
    ("/ui/reporting/report_building", "src/analyst_actions/build_report/ui"),
    ("/ui/reporting/conversational_bi", "src/business_suite/conversational_bi/ui"),
    ("/ui/reporting/proactive_insights", "src/business_suite/proactive_alerts/ui"),
    ("/ui/reporting/dashboards", "src/business_suite/dashboards/ui"),
    ("/ui/business_analytics/insight_discovery", "src/business_suite/deep_insights/ui"),
    ("/ui/business_analytics/root_cause_analysis", "src/analyst_actions/root_cause_analysis/ui"),
    ("/ui/business_analytics/what_if_analysis", "src/business_suite/scenario_analysis/ui"),
    ("/ui/business_analytics/business_narratives", "src/analyst_actions/recommend_actions/ui"),
    ("/ui/db_explorer", "src/analyst_actions/explore_data/ui")
]

main_dir = os.path.dirname(os.path.abspath(__file__))

for mount_url, local_dir in sub_apps_paths:
    rel_path = local_dir.replace("src/", "", 1) if local_dir.startswith("src/") else local_dir
    abs_local_dir = os.path.abspath(os.path.join(main_dir, rel_path))
    os.makedirs(abs_local_dir, exist_ok=True)
    app.mount(mount_url, NoCacheStaticFiles(directory=abs_local_dir, html=True))

# 3. Mount the master UI platform shell onto root "/"
master_ui_dir = os.path.abspath(os.path.join(main_dir, 'ui'))
if os.path.exists(master_ui_dir):
    app.mount("/", NoCacheStaticFiles(directory=master_ui_dir, html=True), name="ui_master")
else:
    @app.get("/")
    async def index():
        return {'status': 'active', 'message': 'AIP Master Shell not loaded.'}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
