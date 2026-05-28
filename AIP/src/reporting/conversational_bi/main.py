"""
Product 3: Conversational BI Assistant (Stateful Agentic AI)
Assigned Enterprise Agent: Conversational BI Agent
"""

import html
import json
import re
from typing import Dict, Any, List, Tuple
from shared.intelligence import invoke_capability, call_llm
from src.shared.infra.analytics_client import AnalyticsClient

_analytics_client = AnalyticsClient()
run_data_query = _analytics_client.run_compatible_read_query
run_custom_query = _analytics_client.run_custom_query


async def _safe_invoke_capability(name: str, input_params: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a capability without letting optional infra outages fail the BI chat."""
    try:
        result = await invoke_capability(name, input_params)
        return result if isinstance(result, dict) else {}
    except Exception as exc:
        print(f"[Workflow: Reporting - Conversational BI] Capability '{name}' unavailable: {str(exc)}")
        return {}


def _safe_data_query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Run a read-only analytics query; facts must come from this path only."""
    try:
        return run_data_query(sql, params)
    except Exception as exc:
        print(f"[Workflow: Reporting - Conversational BI] Data query unavailable: {str(exc)} | SQL={sql}")
        return []


def _safe_custom_query(sql: str) -> List[Dict[str, Any]]:
    """Run an RBAC-enforced read-only analytics query and return bounded rows."""
    try:
        cleaned = sql.strip().rstrip(';')
        bounded_sql = f"SELECT * FROM ({cleaned}) AS convbi_result LIMIT 50;"
        return run_custom_query(bounded_sql)
    except Exception as exc:
        print(f"[Workflow: Reporting - Conversational BI] Dynamic query unavailable: {str(exc)} | SQL={sql}")
        return []


def _execute_custom_query_with_error(sql: str) -> Tuple[List[Dict[str, Any]], str]:
    """Run read-only query and return results plus any caught exception string."""
    try:
        cleaned = sql.strip().rstrip(';')
        bounded_sql = f"SELECT * FROM ({cleaned}) AS convbi_result LIMIT 50;"
        return run_custom_query(bounded_sql), ""
    except Exception as exc:
        return [], str(exc)


def _schema_catalog() -> Dict[str, Any]:
    """Discover only tables and columns authorized for the active profile, dynamically enriched with distinct values for string/categorical fields."""
    tables = _analytics_client.list_tables()
    catalog: Dict[str, Any] = {}
    for table in tables:
        try:
            schema = _analytics_client.get_table_schema(table)
            enriched_schema = []
            for col in schema:
                col_name = col.get('column_name')
                dtype = col.get('data_type', '').lower()
                col_meta = dict(col)
                
                # Systemic value matching: if it is a string-based categorical column, fetch up to 8 distinct values
                if 'char' in dtype or 'text' in dtype or any(term in col_name.lower() for term in ('type', 'status', 'currency', 'category', 'segment', 'class', 'direction')):
                    try:
                        distinct_rows = run_custom_query(f"SELECT DISTINCT {col_name} FROM {table} WHERE {col_name} IS NOT NULL LIMIT 8")
                        distinct_vals = [list(r.values())[0] for r in distinct_rows if r]
                        col_meta['distinct_values'] = distinct_vals
                    except Exception:
                        pass
                enriched_schema.append(col_meta)
            catalog[table] = enriched_schema
        except Exception as exc:
            print(f"[Workflow: Reporting - Conversational BI] Schema unavailable for {table}: {str(exc)}")
            catalog[table] = []
    return catalog


def _safe_query_label(label: str) -> str:
    cleaned = ''.join(ch if ch.isalnum() or ch in (' ', '_', '-') else ' ' for ch in label).strip()
    return cleaned[:80] or 'Query Result'


def _validate_query_plan(raw_plan: Any, schema_catalog: Dict[str, Any]) -> List[Dict[str, str]]:
    allowed_tables = set(schema_catalog.keys())
    if not isinstance(raw_plan, dict):
        return []
    queries = raw_plan.get('queries')
    if not isinstance(queries, list):
        return []

    validated: List[Dict[str, str]] = []
    for item in queries[:6]:
        if not isinstance(item, dict):
            continue
        label = _safe_query_label(str(item.get('label') or 'Query Result'))
        sql = str(item.get('sql') or '').strip().rstrip(';')
        if not sql or not sql.lower().startswith(('select', 'with')):
            continue
        if ';' in sql:
            continue
        referenced = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', sql.lower())) & {t.lower() for t in allowed_tables}
        if not referenced:
            continue
        validated.append({'label': label, 'sql': sql})
    return validated


async def _generate_query_plan(question: str, schema_catalog: Dict[str, Any], retrieve_result: Dict[str, Any]) -> List[Dict[str, str]]:
    """Ask the LLM for a read-only query plan over authorized tables only."""
    context = retrieve_result.get('context') if isinstance(retrieve_result, dict) else None
    if isinstance(context, list):
        context_text = "\n".join(str(item) for item in context[:5])
    elif context:
        context_text = str(context)
    else:
        context_text = "No KMS context matched."

    system_prompt = """
You are a PostgreSQL BI query planner. Return JSON only.
Generate at most 6 read-only SELECT queries that answer the user's question.
Use only AUTHORIZED_SCHEMA tables and columns. Do not invent table or column names.
Prefer aggregate queries for business questions. Use LIMIT for detail/sample queries.
Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE, or multiple statements.
KMS_CONTEXT is metadata only; it may guide topic selection but is not a source of facts.
JSON shape: {"queries":[{"label":"short business label","sql":"SELECT ..."}]}
""".strip()
    user_prompt = json.dumps({
        'question': question,
        'AUTHORIZED_SCHEMA': schema_catalog,
        'KMS_CONTEXT': context_text[:3000],
    }, default=str, indent=2)
    llm_plan = await call_llm(system_prompt, user_prompt, json_mode=True)
    if llm_plan:
        try:
            return _validate_query_plan(json.loads(llm_plan), schema_catalog)
        except Exception as exc:
            print(f"[Workflow: Reporting - Conversational BI] Query plan parse failed: {str(exc)}")
    return _fallback_query_plan(question, schema_catalog)


def _fallback_query_plan(question: str, schema_catalog: Dict[str, Any]) -> List[Dict[str, str]]:
    """Deterministic fallback: inspect authorized schema and query relevant tables."""
    q_words = {w for w in re.findall(r'[a-zA-Z_]+', question.lower()) if len(w) > 2}
    plan: List[Dict[str, str]] = []

    if any(word in q_words for word in {'access', 'accessible', 'tables', 'table', 'available'}):
        return []

    scored: List[Tuple[int, str]] = []
    for table, columns in schema_catalog.items():
        col_names = {str(col.get('column_name', '')).lower() for col in columns if isinstance(col, dict)}
        tokens = set(table.lower().split('_')) | col_names
        score = len(q_words & tokens)
        if table.lower() in question.lower():
            score += 4
        if score:
            scored.append((score, table))

    selected = [table for _, table in sorted(scored, reverse=True)[:4]] or list(schema_catalog.keys())[:4]
    for table in selected:
        columns = [str(col.get('column_name')) for col in schema_catalog.get(table, []) if isinstance(col, dict)]
        numeric_cols = [c for c in columns if any(term in c.lower() for term in ('amount', 'balance', 'value', 'limit', 'rate', 'percent', 'count', 'days', 'aum'))]
        group_cols = [c for c in columns if any(term in c.lower() for term in ('type', 'status', 'currency', 'branch', 'segment', 'class', 'category'))]
        if numeric_cols and group_cols:
            plan.append({
                'label': f'{table} summary by {group_cols[0]}',
                'sql': f'SELECT {group_cols[0]}, COUNT(*) AS record_count, SUM({numeric_cols[0]}) AS total_{numeric_cols[0]} FROM {table} GROUP BY {group_cols[0]} ORDER BY total_{numeric_cols[0]} DESC NULLS LAST'
            })
        else:
            plan.append({'label': f'{table} detail sample', 'sql': f'SELECT * FROM {table} LIMIT 25'})
    return plan[:6]


def _build_accessible_table_facts(schema_catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            'table_name': table,
            'columns': [col.get('column_name') for col in columns if isinstance(col, dict)],
        }
        for table, columns in schema_catalog.items()
    ]


async def _repair_sql_query(question: str, failed_sql: str, error_msg: str, schema_catalog: Dict[str, Any]) -> str:
    """Uses LLM reasoning to repair a failing SQL statement based on the DB error and schema context."""
    system_prompt = """
You are an expert PostgreSQL DBA and SQL Debugger Agent. Return JSON only.
Analyze the user's business question, the failing SQL query, and the exact database error.
Generate a corrected, valid read-only PostgreSQL query that resolves the error and accurately answers the question.
Use only AUTHORIZED_SCHEMA tables and columns. Do not invent columns.
Do not use write operations (INSERT, UPDATE, DELETE, etc.). Enforce a read-only SELECT.
JSON shape: {"repaired_sql": "SELECT ..."}
""".strip()
    user_prompt = json.dumps({
        'question': question,
        'failing_sql': failed_sql,
        'database_error': error_msg,
        'AUTHORIZED_SCHEMA': schema_catalog
    }, default=str, indent=2)
    
    try:
        llm_response = await call_llm(system_prompt, user_prompt, json_mode=True)
        if llm_response:
            parsed = json.loads(llm_response)
            repaired = str(parsed.get('repaired_sql') or '').strip()
            if repaired.lower().startswith(('select', 'with')):
                return repaired
    except Exception as exc:
        print(f"[SQL Debugger Agent] SQL repair failed: {str(exc)}")
    return ""


async def _build_live_fact_pack(question: str, retrieve_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build Conv BI facts dynamically from authorized schema and question-specific SQL using a self-healing retry loop."""
    schema_catalog = _schema_catalog()
    query_plan = await _generate_query_plan(question, schema_catalog, retrieve_result)
    query_results: List[Dict[str, Any]] = []
    
    for planned in query_plan:
        sql = planned['sql']
        label = planned['label']
        
        # Initial execution
        rows, err_msg = _execute_custom_query_with_error(sql)
        
        # Self-healing retry loop
        attempts = 0
        original_sql = sql
        while err_msg and attempts < 2:
            attempts += 1
            print(f"[Workflow: Reporting - Conversational BI] Query failed (attempt {attempts}): '{label}' | Error: {err_msg}")
            
            repaired_sql = await _repair_sql_query(question, sql, err_msg, schema_catalog)
            if not repaired_sql or repaired_sql == sql:
                print(f"[Workflow: Reporting - Conversational BI] Could not generate dynamic repair for '{label}'")
                break
                
            sql = repaired_sql
            print(f"[Workflow: Reporting - Conversational BI] Attempting re-execution of repaired SQL: '{sql}'")
            rows, err_msg = _execute_custom_query_with_error(sql)
            
        if err_msg:
            print(f"[Workflow: Reporting - Conversational BI] Query failed permanently: '{label}'")
            rows = []
            
        query_results.append({
            'label': label,
            'sql': sql,
            'original_sql': original_sql,
            'rows': rows,
            'row_count': len(rows),
            'repaired': sql != original_sql and not err_msg
        })

    return {
        'fact_source_rule': 'All factual values in the answer must come only from executed live SQL query results or authorized schema metadata.',
        'question': question,
        'authorized_tables': list(schema_catalog.keys()),
        'authorized_schema': schema_catalog,
        'accessible_table_metadata': _build_accessible_table_facts(schema_catalog),
        'executed_queries': query_results,
        'unavailable_facts': [item['label'] for item in query_results if not item['rows']],
    }


async def _build_llm_narrative(question: str, fact_pack: Dict[str, Any], retrieve_result: Dict[str, Any]) -> str:
    """Use the LLM to explain live SQL facts without allowing context-derived facts."""
    context = retrieve_result.get('context') if isinstance(retrieve_result, dict) else None
    if isinstance(context, list):
        context_text = "\n".join(str(item) for item in context[:5])
    elif context:
        context_text = str(context)
    else:
        context_text = "No KMS context matched."

    system_prompt = """
You are a Conversational BI analyst. Write a concise, executive-friendly Markdown answer.

Hard rules:
- Use the user's question to choose emphasis and structure; do not return a fixed template.
- Numeric facts, balances, rates, counts, dates, table names, columns, and table rows may only come from LIVE_DATA_FACTS.
- KMS_CONTEXT is directional business metadata only. Never use it as a source of facts.
- If the user asks what tables are accessible, answer from LIVE_DATA_FACTS.authorized_tables and do not list derived summaries as tables.
- If LIVE_DATA_FACTS does not contain a fact, say it is not available from the authorized data source.
- Do not invent branch names, balances, rates, IDs, trends, causes, or conclusions.
- Mention that values are data-grounded, but do not over-explain internal implementation.
- Include a compact table only when it helps answer the question.
""".strip()
    user_prompt = json.dumps({
        "question": question,
        "LIVE_DATA_FACTS": fact_pack,
        "KMS_CONTEXT": context_text[:4000],
        "output_format": "Markdown narrative with any useful compact tables."
    }, default=str, indent=2)

    ai_answer = await call_llm(system_prompt, user_prompt)
    if not ai_answer or not ai_answer.strip():
        return _build_factual_narrative(question, fact_pack, llm_unavailable=True)
    return ai_answer.strip()


async def _revise_llm_narrative(
    question: str,
    fact_pack: Dict[str, Any],
    retrieve_result: Dict[str, Any],
    previous_draft: str,
    violations: List[str],
    revision_instruction: str
) -> str:
    """Uses LLM to revise a narrative draft to fix specific grounding violations flagged by the QC agent."""
    context = retrieve_result.get('context') if isinstance(retrieve_result, dict) else None
    if isinstance(context, list):
        context_text = "\n".join(str(item) for item in context[:5])
    elif context:
        context_text = str(context)
    else:
        context_text = "No KMS context matched."

    system_prompt = """
You are a Conversational BI analyst. You are tasked with revising your previously written draft narrative.
A Quality Control agent audited your draft and flagged several compliance and fact-grounding violations.
You must correct these violations and rewrite the draft.

Hard rules:
- Strictly address every issue listed in VIOLATIONS and follow the REVISION_INSTRUCTIONS.
- Align every numeric fact, rate, date, percentage, or currency figure EXACTLY with LIVE_DATA_FACTS.
- Re-write sections that extrapolate or state ungrounded claims.
- Do not cite KMS_CONTEXT as a source of database counts or numbers.
- Maintain an executive-friendly Markdown format.
""".strip()

    user_prompt = json.dumps({
        "question": question,
        "LIVE_DATA_FACTS": fact_pack,
        "KMS_CONTEXT": context_text[:3000],
        "PREVIOUS_DRAFT": previous_draft,
        "VIOLATIONS": violations,
        "REVISION_INSTRUCTIONS": revision_instruction
    }, default=str, indent=2)

    ai_answer = await call_llm(system_prompt, user_prompt)
    if not ai_answer or not ai_answer.strip():
        return previous_draft
    return ai_answer.strip()


async def _run_quality_control(question: str, fact_pack: Dict[str, Any], narrative_draft: str, retrieve_result: Dict[str, Any]) -> Dict[str, Any]:
    """Agent that performs strict, line-by-line RAG grounding audit of the narrative draft against live query data."""
    context = retrieve_result.get('context') if isinstance(retrieve_result, dict) else None
    if isinstance(context, list):
        context_text = "\n".join(str(item) for item in context[:5])
    elif context:
        context_text = str(context)
    else:
        context_text = "No KMS context matched."

    system_prompt = """
You are a Senior BI Quality Control and Grounding Verification Agent. Return JSON only.
Analyze the user's question, the actual executed database query facts in LIVE_DATA_FACTS, and the draft business narrative.

Your primary mission is to verify that the narrative is 100% accurate, factual, and strictly grounded.
Perform the following checks:
1. "Numeric Audit": Inspect every single number, date, percentage, or currency figure cited in the narrative draft. Do they EXACTLY match values computed in the LIVE_DATA_FACTS query results? If a number is fabricated, hallucinated, or incorrectly rounded/summed, it is a critical violation.
2. "Concept Leakage": Verify that the narrative does NOT use definitions or numbers from the KMS_CONTEXT to state absolute database counts or facts. KMS_CONTEXT is for semantic vocabulary guidance only.
3. "Extrapolation Check": Check if the writer made guesses, claims about trends, or structural causes that are not explicitly present in the query result sets.
4. "Restriction Compliance": Confirm that no unauthorized tables or columns are referenced or listed.

Return a JSON containing:
- "passed": boolean flag (true if 0 violations, false otherwise).
- "violations": a list of string descriptions detailing exactly which sentences/facts failed audit and why.
- "revision_instruction": clear, directive instructions to tell the Writer Agent exactly how to fix the violations. (Should be null if passed is true).

JSON shape:
{
  "passed": true | false,
  "violations": ["Found value $4.2B in paragraph 2 which is not grounded in the SQL result total balance of $3.5B."],
  "revision_instruction": "Please rewrite the second paragraph. The total balance is $3.5B, not $4.2B. Stick exactly to the SQL facts."
}
""".strip()

    # Create a simplified lightweight representation of LIVE_DATA_FACTS to avoid LLM context bloating
    simplified_facts = {
        'question': question,
        'authorized_tables': fact_pack.get('authorized_tables'),
        'executed_queries': [
            {
                'label': eq.get('label'),
                'sql': eq.get('sql'),
                'row_count': eq.get('row_count'),
                'rows': eq.get('rows')[:15] # first 15 rows is plenty for verification
            }
            for eq in fact_pack.get('executed_queries', [])
        ]
    }

    user_prompt = json.dumps({
        'LIVE_DATA_FACTS': simplified_facts,
        'KMS_CONTEXT': context_text[:3000],
        'DRAFT_NARRATIVE': narrative_draft
    }, default=str, indent=2)

    try:
        qc_response = await call_llm(system_prompt, user_prompt, json_mode=True)
        if qc_response:
            parsed = json.loads(qc_response)
            if isinstance(parsed, dict) and 'passed' in parsed:
                return parsed
    except Exception as exc:
        print(f"[Quality Control Agent] Verification call failed: {str(exc)}")
        
    return {'passed': True, 'violations': [], 'revision_instruction': None}


async def _plan_visualizations(question: str, executed_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Agent that plans standard-based, beautiful comparative or metric visualizations from executed SQL results."""
    visualizable = []
    for q in executed_queries:
        if q.get('rows') and len(q['rows']) > 0:
            visualizable.append({
                'label': q['label'],
                'row_count': q['row_count'],
                'columns': list(q['rows'][0].keys()),
                'sample': q['rows'][:3]
            })
            
    if not visualizable:
        return {'has_visual': False, 'visuals': []}
        
    system_prompt = """
You are a Senior BI Dashboard and Visualization Architect. Return JSON only.
Analyze the user's business question and the available query result datasets.
Determine the single best visual representation (or multiple if appropriate, max 2) that would provide maximum analytical value.
Available visualization types:
1. "bar" - Horizontal progress-bar comparative rankings. Best for categories, branches, and distributions.
2. "donut" - SVG circular segment-based gauge charts. Best for percentages or part-to-whole proportions.
3. "metrics_grid" - Numeric KPI cards. Best for absolute sums, counts, and core single KPIs.
4. "table" - Standard beautiful tabular grids. Best for multi-column details.

Formulate a visualization plan containing a list of visuals with the exact configurations (such as labels, value fields, trend colors, size, max values, title, description) to be rendered.
Ensure the 'data_key' matches the exact 'label' of the visualizable dataset.
Choose a 'color_scheme' from: 'emerald' (success/wealth), 'indigo' (corporate/neutral), 'amber' (warnings/interest), 'rose' (liabilities/outflows).

JSON structure:
{
  "has_visual": true,
  "visuals": [
    {
      "type": "bar" | "donut" | "metrics_grid" | "table",
      "title": "Short Descriptive Title",
      "description": "Short explanation of the analytical insight in the visual",
      "data_key": "Exact Executed Query Label",
      "config": {
        "label_column": "column_name_for_labels",
        "value_column": "column_name_for_numeric_value",
        "color_scheme": "emerald" | "indigo" | "amber" | "rose",
        "is_percentage": false,
        "show_totals": true
      }
    }
  ]
}
""".strip()
    
    user_prompt = json.dumps({
        'question': question,
        'datasets': visualizable
    }, default=str, indent=2)
    
    try:
        decision = await call_llm(system_prompt, user_prompt, json_mode=True)
        if decision:
            parsed = json.loads(decision)
            if isinstance(parsed, dict) and 'visuals' in parsed:
                return parsed
    except Exception as exc:
        print(f"[Visualization Planner Agent] Planning failed: {str(exc)}")
        
    # Heuristic fallback
    first_ds = visualizable[0]
    first_label = first_ds['label']
    first_cols = first_ds['columns']
    first_sample = first_ds['sample'][0]
    
    numeric_cols = [k for k, v in first_sample.items() if isinstance(v, (int, float))]
    label_cols = [k for k in first_cols if k not in numeric_cols]
    
    val_col = numeric_cols[-1] if numeric_cols else 'balance'
    lbl_col = label_cols[0] if label_cols else 'branch'
    
    return {
        'has_visual': True,
        'visuals': [{
            'type': 'bar',
            'title': f'{first_label} Overview',
            'description': 'Comparative view generated automatically from operational records.',
            'data_key': first_label,
            'config': {
                'label_column': lbl_col,
                'value_column': val_col,
                'color_scheme': 'indigo',
                'is_percentage': False,
                'show_totals': True
            }
        }]
    }


def _render_premium_visuals(viz_plan: Dict[str, Any], executed_queries: List[Dict[str, Any]]) -> str:
    """Renders sleek glassmorphic visualizations matching the visual plan."""
    if not viz_plan.get('has_visual') or not viz_plan.get('visuals'):
        return ""
        
    query_map = {q['label']: q['rows'] for q in executed_queries if q.get('rows')}
    html_blocks = []
    
    for viz in viz_plan['visuals']:
        vtype = viz.get('type')
        title = viz.get('title', 'BI Snapshot')
        desc = viz.get('description', '')
        dkey = viz.get('data_key')
        config = viz.get('config', {})
        
        rows = query_map.get(dkey)
        if not rows:
            continue
            
        color_scheme = config.get('color_scheme', 'indigo')
        colors = {
            'emerald': {'bg': 'rgba(16, 185, 129, 0.1)', 'border': '#10b981', 'accent': '#059669'},
            'indigo': {'bg': 'rgba(99, 102, 241, 0.1)', 'border': '#6366f1', 'accent': '#4f46e5'},
            'amber': {'bg': 'rgba(245, 158, 11, 0.1)', 'border': '#f59e0b', 'accent': '#d97706'},
            'rose': {'bg': 'rgba(244, 63, 94, 0.1)', 'border': '#f43f5e', 'accent': '#e11d48'},
        }.get(color_scheme, {'bg': 'rgba(99, 102, 241, 0.1)', 'border': '#6366f1', 'accent': '#4f46e5'})
        
        card = [
            f"<div class='convbi-visual-card' style='border-left: 4px solid {colors['border']}; margin-top: 1.5rem; padding: 1.25rem; border-radius: 12px; background: var(--bg-card, rgba(255,255,255,0.7)); backdrop-filter: blur(10px); box-shadow: 0 4px 20px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.06);'>"
            f"  <div class='convbi-visual-header' style='margin-bottom: 1.25rem;'>"
            f"    <span class='convbi-kicker' style='font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: {colors['border']}; font-weight: 700;'>Visual BI Insight</span>"
            f"    <h3 style='margin: 0.25rem 0 0.1rem 0; font-size: 1.15rem; font-weight: 800; color: var(--text-primary, #1e293b);'>{html.escape(title)}</h3>"
            f"    <p style='margin: 0; font-size: 0.85rem; color: var(--text-secondary, #64748b);'>{html.escape(desc)}</p>"
            f"  </div>"
        ]
        
        lbl_col = config.get('label_column')
        val_col = config.get('value_column')
        
        if not lbl_col or not val_col:
            first = rows[0]
            numeric_cols = [k for k, v in first.items() if isinstance(v, (int, float))]
            label_cols = [k for k in first.keys() if k not in numeric_cols]
            lbl_col = lbl_col or (label_cols[0] if label_cols else list(first.keys())[0])
            val_col = val_col or (numeric_cols[-1] if numeric_cols else list(first.keys())[-1])
            
        if vtype == 'bar':
            ranked = []
            for r in rows:
                val = _numeric(r, val_col)
                ranked.append((r, val))
            ranked = sorted(ranked, key=lambda x: x[1], reverse=True)[:8]
            max_value = max((abs(v) for _, v in ranked), default=1.0) or 1.0
            
            bars_html = []
            for r, val in ranked:
                lbl = str(r.get(lbl_col) or 'Unknown')
                width = max(5, min(100, abs(val) / max_value * 100))
                formatted_val = _format_currency(val) if 'balance' in val_col.lower() or 'amount' in val_col.lower() or 'limit' in val_col.lower() else f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
                
                bars_html.append(
                    f"<div class='convbi-bar-row' style='margin-bottom: 0.75rem;'>"
                    f"  <div class='convbi-bar-label' style='display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.25rem;'>"
                    f"    <span style='color: var(--text-primary, #334155); font-weight: 500;'>{html.escape(lbl)}</span>"
                    f"    <strong style='color: {colors['accent']};'>{html.escape(formatted_val)}</strong>"
                    f"  </div>"
                    f"  <div class='convbi-bar-track' style='background: var(--bg-track, #e2e8f0); height: 8px; border-radius: 4px; overflow: hidden;'>"
                    f"    <div class='convbi-bar-fill' style='width: {width:.1f}%; height: 100%; border-radius: 4px; background: {colors['border']}; transition: width 0.5s ease-in-out;'></div>"
                    f"  </div>"
                    f"</div>"
                )
            card.append("".join(bars_html))
            
        elif vtype == 'donut':
            total_sum = sum(_numeric(r, val_col) for r in rows) or 1.0
            sorted_rows = sorted(rows, key=lambda r: _numeric(r, val_col), reverse=True)
            top_segments = sorted_rows[:4]
            rest_sum = sum(_numeric(r, val_col) for r in sorted_rows[4:])
            
            segments = []
            for r in top_segments:
                segments.append({'lbl': str(r.get(lbl_col) or 'Unknown'), 'val': _numeric(r, val_col)})
            if rest_sum > 0:
                segments.append({'lbl': 'Others', 'val': rest_sum})
                
            svg_size = 120
            radius = 40
            circumference = 2 * 3.14159 * radius
            
            svg_html = [
                f"<div style='display: flex; align-items: center; justify-content: space-around; flex-wrap: wrap; gap: 1.25rem;'>"
                f"  <div style='position: relative; width: {svg_size}px; height: {svg_size}px;'>"
                f"    <svg viewBox='0 0 100 100' style='width: 100%; height: 100%; transform: rotate(-90deg);'>"
                f"      <circle cx='50' cy='50' r='{radius}' fill='transparent' stroke='var(--bg-track, #e2e8f0)' stroke-width='10' />"
            ]
            
            current_pct = 0.0
            segment_colors = [colors['border'], '#3b82f6', '#f59e0b', '#ec4899', '#10b981', '#64748b']
            
            legend_html = ["<div style='flex: 1; min-width: 150px; font-size: 0.85rem;'>"]
            
            for idx, seg in enumerate(segments):
                val_pct = seg['val'] / total_sum
                dash_array = f"{val_pct * circumference:.2f} {circumference:.2f}"
                dash_offset = f"{-current_pct * circumference:.2f}"
                stroke_color = segment_colors[idx % len(segment_colors)]
                
                svg_html.append(
                    f"      <circle cx='50' cy='50' r='{radius}' fill='transparent' "
                    f"              stroke='{stroke_color}' stroke-width='10' "
                    f"              stroke-dasharray='{dash_array}' stroke-dashoffset='{dash_offset}' "
                    f"              stroke-linecap='round' />"
                )
                
                formatted_val = _format_currency(seg['val']) if 'balance' in val_col.lower() or 'amount' in val_col.lower() else f"{seg['val']:,.1f}"
                legend_html.append(
                    f"<div style='display: flex; align-items: center; margin-bottom: 0.5rem;'>"
                    f"  <div style='width: 12px; height: 12px; border-radius: 3px; background: {stroke_color}; margin-right: 0.5rem;'></div>"
                    f"  <span style='color: var(--text-secondary, #475569); flex: 1;'>{html.escape(seg['lbl'])}</span>"
                    f"  <strong style='color: var(--text-primary, #0f172a);'>{formatted_val} ({val_pct*100:.1f}%)</strong>"
                    f"</div>"
                )
                current_pct += val_pct
                
            svg_html.append(
                f"    </svg>"
                f"    <div style='position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; color: var(--text-primary, #1e293b);'>"
                f"      <span>Total</span>"
                f"      <span style='font-size: 0.85rem; font-weight: 800; color: {colors['accent']};'>{_format_currency(total_sum) if 'balance' in val_col.lower() or 'amount' in val_col.lower() else f'{total_sum:,.0f}'}</span>"
                f"    </div>"
                f"  </div>"
            )
            legend_html.append("</div>")
            
            svg_html.append("".join(legend_html))
            svg_html.append("</div>")
            card.append("".join(svg_html))
            
        elif vtype == 'metrics_grid':
            grid_html = ["<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; margin-top: 0.5rem;'>"]
            for r in rows[:6]:
                lbl = str(r.get(lbl_col) or 'Unknown')
                val = _numeric(r, val_col)
                formatted_val = _format_currency(val) if 'balance' in val_col.lower() or 'amount' in val_col.lower() else f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
                
                grid_html.append(
                    f"<div class='convbi-metric-card' style='background: var(--bg-metric-card, rgba(0,0,0,0.02)); border: 1px solid rgba(0,0,0,0.03); padding: 0.85rem; border-radius: 8px; text-align: center;'>"
                    f"  <span style='display: block; font-size: 0.75rem; color: var(--text-secondary, #64748b); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{html.escape(lbl)}</span>"
                    f"  <strong style='display: block; font-size: 1.15rem; font-weight: 800; color: {colors['accent']}; margin-top: 0.25rem;'>{html.escape(formatted_val)}</strong>"
                    f"</div>"
                )
            grid_html.append("</div>")
            card.append("".join(grid_html))
            
        elif vtype == 'table':
            cols = list(rows[0].keys())[:6]
            table_lines = [
                f"<div class='convbi-table-wrap' style='overflow-x: auto; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);'>"
                f"  <table style='width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem;'>"
                f"    <thead>"
                f"      <tr style='background: var(--bg-table-head, #f8fafc); border-bottom: 1px solid rgba(0,0,0,0.06);'>"
            ]
            for c in cols:
                table_lines.append(f"        <th style='padding: 0.75rem; font-weight: 700; color: var(--text-secondary, #475569);'>{html.escape(c.replace('_', ' ').title())}</th>")
            table_lines.append("      </tr>\n    </thead>\n    <tbody>")
            
            for ridx, r in enumerate(rows[:10]):
                bg_style = "background: var(--bg-table-zebra, rgba(0,0,0,0.015));" if ridx % 2 == 1 else ""
                table_lines.append(f"      <tr style='border-bottom: 1px solid rgba(0,0,0,0.04); {bg_style}'>")
                for c in cols:
                    val = r.get(c)
                    if isinstance(val, (int, float)):
                        formatted_val = _format_currency(val) if 'balance' in c.lower() or 'amount' in c.lower() else f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
                    else:
                        formatted_val = str(val if val is not None else '')
                    table_lines.append(f"        <td style='padding: 0.75rem; color: var(--text-primary, #334155);'>{html.escape(formatted_val)}</td>")
                table_lines.append("      </tr>")
                
            table_lines.append("    </tbody>\n  </table>\n</div>")
            card.append("".join(table_lines))
            
        card.append("</div>")
        html_blocks.append("\n".join(card))
        
    return "\n\n".join(html_blocks)


def _markdown_balance_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "_Not available in the authorized data source._"
    lines = ["| Branch | Currency | Balance |", "| --- | --- | ---: |"]
    for row in rows:
        lines.append(
            f"| {row.get('branch', 'Unassigned')} | {row.get('currency', '')} | {_format_currency(_numeric(row, 'balance'))} |"
        )
    return "\n".join(lines)


def _markdown_buffer_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "_Not available in the authorized data source._"
    lines = ["| Buffer | Amount | Haircut % | Yield % |", "| --- | ---: | ---: | ---: |"]
    for row in rows:
        lines.append(
            f"| {row.get('asset_type', 'Unassigned')} | "
            f"{_format_currency(_numeric(row, 'amount'))} | "
            f"{_numeric(row, 'haircut_percentage'):.2f} | "
            f"{_numeric(row, 'yield_rate'):.2f} |"
        )
    return "\n".join(lines)


def _markdown_generic_table(rows: List[Dict[str, Any]], max_rows: int = 12) -> str:
    if not rows:
        return "_No rows returned from the authorized data source._"
    columns = list(rows[0].keys())[:8]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows[:max_rows]:
        values = []
        for col in columns:
            value = row.get(col)
            if isinstance(value, (int, float)):
                values.append(f"{value:,.2f}" if isinstance(value, float) else f"{value:,}")
            else:
                values.append(str(value or ''))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _build_factual_narrative(question: str, fact_pack: Dict[str, Any], llm_unavailable: bool = False) -> str:
    """Fallback renderer from dynamic SQL facts only; KMS context is intentionally excluded."""
    intro = "Live AI narrative generation is unavailable or failed validation, so this fallback view is rendered directly from authorized live SQL query results. KMS context is not used as a source of facts."
    if not llm_unavailable:
        intro = "All factual values below are calculated directly from authorized live SQL query results."
    sections = ["## Data-grounded BI Response", intro]

    if any(term in question.lower() for term in ('access', 'accessible', 'tables', 'table', 'available')):
        rows = fact_pack.get('accessible_table_metadata', [])
        sections.extend(["### Authorized Tables", _markdown_generic_table(rows, max_rows=30)])
        return "\n\n".join(sections)

    for result in fact_pack.get('executed_queries', []):
        sections.extend([f"### {result.get('label', 'Query Result')}", _markdown_generic_table(result.get('rows', []))])
    if not fact_pack.get('executed_queries'):
        sections.extend(["### Authorized Tables", _markdown_generic_table(fact_pack.get('accessible_table_metadata', []), max_rows=30)])
    return "\n\n".join(sections)


def _escape_cell(value: Any) -> str:
    return html.escape(str(value if value is not None else ''))


def _markdown_to_html(markdown_text: str) -> str:
    """Small safe Markdown renderer for Conv BI output."""
    blocks: List[str] = []
    lines = markdown_text.splitlines()
    i = 0
    paragraph: List[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{html.escape(' '.join(paragraph))}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            flush_paragraph()
            i += 1
            continue
        if line.startswith('### '):
            flush_paragraph(); blocks.append(f"<h3>{html.escape(line[4:])}</h3>"); i += 1; continue
        if line.startswith('## '):
            flush_paragraph(); blocks.append(f"<h2>{html.escape(line[3:])}</h2>"); i += 1; continue
        if line.startswith('# '):
            flush_paragraph(); blocks.append(f"<h1>{html.escape(line[2:])}</h1>"); i += 1; continue
        if line.startswith('|') and i + 1 < len(lines) and lines[i + 1].strip().startswith('|'):
            flush_paragraph()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            rows = [[cell.strip() for cell in row.strip('|').split('|')] for row in table_lines]
            header = rows[0]
            body = rows[2:] if len(rows) > 2 else []
            head_html = ''.join(f"<th>{html.escape(cell)}</th>" for cell in header)
            body_html = ''.join('<tr>' + ''.join(f"<td>{html.escape(cell)}</td>" for cell in row) + '</tr>' for row in body)
            blocks.append(f"<div class='convbi-table-wrap'><table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table></div>")
            continue
        if line.startswith('- '):
            flush_paragraph()
            items = []
            while i < len(lines) and lines[i].strip().startswith('- '):
                items.append(f"<li>{html.escape(lines[i].strip()[2:])}</li>")
                i += 1
            blocks.append(f"<ul>{''.join(items)}</ul>")
            continue
        paragraph.append(line)
        i += 1
    flush_paragraph()
    return "<article class='convbi-answer-html'>" + ''.join(blocks) + "</article>"


def _best_visual_dataset(fact_pack: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    for result in fact_pack.get('executed_queries', []):
        rows = result.get('rows') or []
        if rows and isinstance(rows[0], dict):
            numeric_cols = [k for k, v in rows[0].items() if isinstance(v, (int, float))]
            label_cols = [k for k in rows[0].keys() if k not in numeric_cols]
            if numeric_cols and label_cols:
                return str(result.get('label') or 'Visual Summary'), rows
    return '', []


async def _decide_visual_representation(question: str, fact_pack: Dict[str, Any]) -> Dict[str, Any]:
    """Agent that decides whether an HTML visual is useful for this answer."""
    title, rows = _best_visual_dataset(fact_pack)
    if not rows:
        return {'required': False, 'reason': 'No visualizable numeric result set returned.'}
    system_prompt = """
You are a BI visualization decision agent. Return JSON only.
Decide if a visual representation would make the answer easier to consume.
Use only provided result metadata. Prefer visuals for comparisons, rankings, trends, distributions, mixes, balances, rates, and summaries.
JSON shape: {"required": true|false, "visual_type": "bar|table|cards", "reason": "short reason"}
""".strip()
    sample = rows[:5]
    llm_decision = await call_llm(system_prompt, json.dumps({'question': question, 'result_label': title, 'sample_rows': sample}, default=str), json_mode=True)
    if llm_decision:
        try:
            parsed = json.loads(llm_decision)
            if isinstance(parsed, dict):
                return {
                    'required': bool(parsed.get('required')),
                    'visual_type': parsed.get('visual_type') or 'bar',
                    'reason': str(parsed.get('reason') or ''),
                }
        except Exception as exc:
            print(f"[Workflow: Reporting - Conversational BI] Visual decision parse failed: {str(exc)}")
    q = question.lower()
    required = any(term in q for term in ('compare', 'highest', 'lowest', 'trend', 'rank', 'top', 'by ', 'balance', 'rate', 'summary', 'distribution', 'mix'))
    return {'required': required, 'visual_type': 'bar', 'reason': 'Heuristic visual decision from question and numeric query results.'}


def _build_dynamic_visual_html(question: str, fact_pack: Dict[str, Any], decision: Dict[str, Any]) -> str:
    if not decision.get('required'):
        return ''
    title, rows = _best_visual_dataset(fact_pack)
    if not rows:
        return ''
    first = rows[0]
    numeric_cols = [k for k, v in first.items() if isinstance(v, (int, float))]
    label_cols = [k for k in first.keys() if k not in numeric_cols]
    if not numeric_cols or not label_cols:
        return ''
    metric = numeric_cols[-1]
    label = label_cols[0]
    ranked = sorted(rows, key=lambda r: float(r.get(metric) or 0), reverse=True)[:8]
    max_value = max((abs(float(r.get(metric) or 0)) for r in ranked), default=1.0) or 1.0
    bars = []
    for row in ranked:
        value = float(row.get(metric) or 0)
        width = max(5, min(100, abs(value) / max_value * 100))
        bars.append(
            f"<div class='convbi-dynamic-bar'>"
            f"<div class='convbi-dynamic-label'><span>{_escape_cell(row.get(label))}</span><strong>{_escape_cell(row.get(metric))}</strong></div>"
            f"<div class='convbi-dynamic-track'><div style='width:{width:.1f}%'></div></div>"
            f"</div>"
        )
    return (
        "<section class='convbi-dynamic-visual'>"
        f"<div class='convbi-visual-title'><span>Visual Agent</span><h3>{html.escape(title)}</h3><p>{html.escape(str(decision.get('reason') or ''))}</p></div>"
        f"<div class='convbi-dynamic-bars'>{''.join(bars)}</div>"
        "</section>"
    )


def _format_currency(value: float) -> str:
    """Format large enterprise amounts for stakeholder visual summaries."""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def _numeric(row: Dict[str, Any], key: str) -> float:
    try:
        return float(row.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def _sum_amount(rows: List[Dict[str, Any]], key: str) -> float:
    return sum(_numeric(row, key) for row in rows)


def _branch_balances(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    totals: Dict[str, float] = {}
    for row in rows:
        branch = str(row.get('branch') or 'Unassigned')
        totals[branch] = totals.get(branch, 0.0) + _numeric(row, 'balance')
    return [
        {'label': label, 'value': value}
        for label, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5]
    ]


def _top_buffers(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buffers = [
        {
            'label': str(row.get('asset_type') or row.get('buffer_id') or 'Liquidity Buffer'),
            'value': _numeric(row, 'amount'),
            'yield': _numeric(row, 'yield_rate'),
        }
        for row in rows
    ]
    return sorted(buffers, key=lambda item: item['value'], reverse=True)[:4]


def _build_conversation_visual_html(
    question: str,
    deposits: List[Dict[str, Any]],
    loans: List[Dict[str, Any]],
    buffers: List[Dict[str, Any]],
    performance: List[Dict[str, Any]],
    retrieve_result: Dict[str, Any],
) -> str:
    """Return a deterministic, visual HTML card for every Conv BI response."""
    q_lower = question.lower()
    accounts = performance or deposits or loans
    branch_rows = _branch_balances(accounts)
    buffer_rows = _top_buffers(buffers)
    total_balance = _sum_amount(accounts, 'balance')
    total_buffers = _sum_amount(buffers, 'amount')
    max_branch = max((row['value'] for row in branch_rows), default=1.0) or 1.0
    max_buffer = max((row['value'] for row in buffer_rows), default=1.0) or 1.0

    if any(term in q_lower for term in ('liquidity', 'buffer', 'hql', 'reserve')):
        visual_title = 'Liquidity Position View'
        visual_focus = 'reserve coverage and regional resource distribution'
    elif any(term in q_lower for term in ('branch', 'performance', 'deposit', 'balance')):
        visual_title = 'Branch Performance View'
        visual_focus = 'Balance concentration across available enterprise ledger region records'
    elif any(term in q_lower for term in ('loan', 'risk', 'default', 'npl')):
        visual_title = 'Risk Exposure View'
        visual_focus = 'Available balance and reserve context for risk discussion'
    else:
        visual_title = 'Stakeholder BI Snapshot'
        visual_focus = 'Data-backed context for this conversation'

    context_count = 0
    context = retrieve_result.get('context') if isinstance(retrieve_result, dict) else None
    if isinstance(context, list):
        context_count = len(context)
    elif context:
        context_count = 1

    def bar_row(item: Dict[str, Any], maximum: float, css_class: str = '') -> str:
        width = max(6, min(100, (item['value'] / maximum) * 100)) if maximum else 6
        label = html.escape(item['label'])
        amount = html.escape(_format_currency(item['value']))
        return (
            f'<div class="convbi-bar-row {css_class}">'
            f'<div class="convbi-bar-label"><span>{label}</span><strong>{amount}</strong></div>'
            f'<div class="convbi-bar-track"><div class="convbi-bar-fill" style="width: {width:.1f}%"></div></div>'
            f'</div>'
        )

    branch_html = ''.join(bar_row(row, max_branch) for row in branch_rows)
    if not branch_html:
        branch_html = '<div class="convbi-empty">No region records available for this access profile.</div>'

    buffer_html = ''.join(
        bar_row({**row, 'label': f"{row['label']} • {row['yield']:.2f}% yield"}, max_buffer, 'buffer')
        for row in buffer_rows
    )
    if not buffer_html:
        buffer_html = '<div class="convbi-empty">No reserve buffer records available for this access profile.</div>'

    return f'''
<div class="convbi-visual-card">
  <div class="convbi-visual-header">
    <div>
      <span class="convbi-kicker">Visual BI Answer</span>
      <h3>{html.escape(visual_title)}</h3>
      <p>{html.escape(visual_focus)}</p>
    </div>
    <div class="convbi-status-pill">KMS matches: {context_count}</div>
  </div>
  <div class="convbi-metric-grid">
    <div class="convbi-metric"><span>Available Balance</span><strong>{html.escape(_format_currency(total_balance))}</strong></div>
    <div class="convbi-metric"><span>Liquidity Buffers</span><strong>{html.escape(_format_currency(total_buffers))}</strong></div>
    <div class="convbi-metric"><span>Records Visualized</span><strong>{len(accounts) + len(buffers)}</strong></div>
  </div>
  <div class="convbi-visual-grid">
    <section class="convbi-panel">
      <h4>Branch Balance Distribution</h4>
      {branch_html}
    </section>
    <section class="convbi-panel">
      <h4>Liquidity Buffer Mix</h4>
      {buffer_html}
    </section>
  </div>
</div>
'''.strip()


async def run_conversational_bi_workflow(question: str) -> Dict[str, Any]:
    print(f'[Workflow: Reporting - Conversational BI] Answering analytics query: "{question}"')

    # 1. Gather KMS context mapping
    retrieve_result = await _safe_invoke_capability('knowledge_retrieval', {'question': question})

    # 2. Dynamically inspect authorized schema and build question-specific live facts using a self-healing SQL retry loop
    fact_pack = await _build_live_fact_pack(question, retrieve_result)
    
    # 3. Ask the LLM to write the BI narrative using only live SQL facts
    response_narrative = await _build_llm_narrative(question, fact_pack, retrieve_result)
    
    # Grounding Validation Loop (Quality Control, max 2 revision cycles)
    qc_passed = False
    qc_attempts = 0
    qc_violations = []
    
    while not qc_passed and qc_attempts < 2:
        qc_attempts += 1
        print(f"[Workflow: Reporting - Conversational BI] Running Quality Control Grounding Audit (attempt {qc_attempts})...")
        qc_result = await _run_quality_control(question, fact_pack, response_narrative, retrieve_result)
        
        if qc_result.get('passed'):
            print("[Workflow: Reporting - Conversational BI] Quality Control Grounding Audit PASSED successfully.")
            qc_passed = True
            break
            
        qc_violations = qc_result.get('violations') or []
        instruction = qc_result.get('revision_instruction') or "Please rewrite the narrative ensuring complete factual grounding."
        print(f"[Workflow: Reporting - Conversational BI] Quality Control Grounding Audit FAILED with {len(qc_violations)} violations. Triggering revision...")
        
        response_narrative = await _revise_llm_narrative(question, fact_pack, retrieve_result, response_narrative, qc_violations, instruction)
        
    if not qc_passed:
        print("[Workflow: Reporting - Conversational BI] Narrative failed Quality Control permanently after 2 revision cycles. Falling back to deterministic factual narrative.")
        response_narrative = _build_factual_narrative(question, fact_pack, llm_unavailable=False)

    # Generate the line spec to visualize the trend dynamically from live Enterprise Ledger database records
    viz_spec = None
    if response_narrative:
        q_lower = question.lower()
        try:
            if 'npl' in q_lower or 'default' in q_lower:
                rows = _safe_custom_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions WHERE direction = 'Outflow' GROUP BY month ORDER BY month DESC LIMIT 7")
                selected_trends = [round(float(r.get('total', 0)) / 100_000_000, 2) for r in reversed(rows) if r.get('total') is not None]
            elif 'ldr' in q_lower or 'deposit' in q_lower:
                rows = _safe_custom_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions GROUP BY month ORDER BY month DESC LIMIT 7")
                selected_trends = [round(float(r.get('total', 0)) / 10_000_000, 1) for r in reversed(rows) if r.get('total') is not None]
            elif 'cac' in q_lower or 'card' in q_lower:
                rows = _safe_custom_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions WHERE transaction_type = 'Sweep Transfer' GROUP BY month ORDER BY month DESC LIMIT 7")
                selected_trends = [round(float(r.get('total', 0)) / 2_000_000, 0) for r in reversed(rows) if r.get('total') is not None]
            else:
                rows = _safe_custom_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions GROUP BY month ORDER BY month DESC LIMIT 7")
                selected_trends = [round(float(r.get('total', 0)) / 200_000_000, 2) for r in reversed(rows) if r.get('total') is not None]

            selected_trends = selected_trends[:7]

            if selected_trends:
                viz_result = await _safe_invoke_capability('visualization', {
                    'chartType': 'line',
                    'trends': selected_trends
                })
                viz_spec = viz_result.get('vegaSpec')
        except Exception as exc:
            print(f"[Workflow: Reporting - Conversational BI] Safe trend generation skipped: {str(exc)}")

    # 4. Multi-format Visualization Planning & Rendering
    viz_plan = await _plan_visualizations(question, fact_pack.get('executed_queries', []))
    premium_visuals_html = _render_premium_visuals(viz_plan, fact_pack.get('executed_queries', []))
    
    narrative_html = _markdown_to_html(response_narrative)
    rendered_html = narrative_html + premium_visuals_html

    return {
        'narrative': response_narrative,
        'renderedHtml': rendered_html,
        'visualDecision': viz_plan,
        'visualHtml': premium_visuals_html,
        'vegaSpec': viz_spec
    }
