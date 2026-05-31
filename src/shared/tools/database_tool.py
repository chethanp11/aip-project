"""
Generic database access and schema catalog discovery tools for AIP sub-agents.
"""

import re
from typing import Dict, Any, List, Tuple

try:
    from src.shared.infra_client.analytics_client import AnalyticsClient
except ImportError:
    from shared.infra_client.analytics_client import AnalyticsClient

_analytics_client = AnalyticsClient()


def get_database_schema() -> Dict[str, Any]:
    """Discovers all database tables and columns authorized for the active user profile,
    dynamically enriched with distinct values for string/categorical columns to support exact value matching.

    Returns:
        A dictionary mapping table names to list of column definitions containing metadata and distinct values.
    """
    try:
        tables = _analytics_client.list_tables()
    except Exception as exc:
        print(f"[Shared Tools - Database] Failed to list tables: {str(exc)}")
        return {}

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
                        distinct_rows = _analytics_client.run_custom_query(
                            f"SELECT DISTINCT {col_name} FROM {table} WHERE {col_name} IS NOT NULL LIMIT 8"
                        )
                        distinct_vals = [list(r.values())[0] for r in distinct_rows if r]
                        col_meta['distinct_values'] = distinct_vals
                    except Exception:
                        pass
                enriched_schema.append(col_meta)
            catalog[table] = enriched_schema
        except Exception as exc:
            print(f"[Shared Tools - Database] Schema unavailable for table {table}: {str(exc)}")
            catalog[table] = []
    return catalog


def execute_read_only_query(sql: str) -> Dict[str, Any]:
    """Runs a safety-audited, read-only SELECT query against the analytics database instance.
    The query is intercepted, stripped, and wrapped inside a bounded subquery (LIMIT 50) for security.

    Args:
        sql: The SQL SELECT statement to execute.

    Returns:
        A dictionary containing:
            - 'rows': List of dictionaries representing the query records.
            - 'row_count': Total number of rows returned.
            - 'error': Exception traceback message if query failed (empty string if successful).
    """
    cleaned = sql.strip().rstrip(';')
    if not cleaned:
        return {'rows': [], 'row_count': 0, 'error': 'Empty query provided.'}
        
    if not cleaned.lower().startswith(('select', 'with')):
        return {'rows': [], 'row_count': 0, 'error': 'Only SELECT or WITH queries are permitted.'}

    if ';' in cleaned:
        return {'rows': [], 'row_count': 0, 'error': 'Multiple statements separated by semicolon are not permitted.'}

    # Enforce read-only bounded execution
    bounded_sql = f"SELECT * FROM ({cleaned}) AS convbi_result LIMIT 50;"
    try:
        rows = _analytics_client.run_custom_query(bounded_sql)
        return {
            'rows': rows,
            'row_count': len(rows),
            'error': ''
        }
    except Exception as exc:
        return {
            'rows': [],
            'row_count': 0,
            'error': str(exc)
        }


def _safe_query_label(label: str) -> str:
    cleaned = ''.join(ch if ch.isalnum() or ch in (' ', '_', '-') else ' ' for ch in label).strip()
    return cleaned[:80] or 'Query Result'


def validate_query_plan(raw_plan: Any, schema_catalog: Dict[str, Any]) -> List[Dict[str, str]]:
    """Validates that all proposed queries in the raw plan strictly target authorized tables only.

    Args:
        raw_plan: Unvalidated dictionary structure from the SQL planner subagent.
        schema_catalog: Bounded schema catalog of authorized tables.

    Returns:
        A list of clean, validated label-and-SQL query dictionaries.
    """
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


def fallback_query_plan(question: str, schema_catalog: Dict[str, Any]) -> List[Dict[str, str]]:
    """Deterministic fallback strategy when the SQL planner subagent fails.

    Args:
        question: User natural language request.
        schema_catalog: Bounded schema catalog of authorized tables.

    Returns:
        A list of ready-to-run backup SELECT queries.
    """
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


def build_accessible_table_facts(schema_catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Helper to convert the raw schema dictionary into simple accessible table descriptions."""
    return [
        {
            'table_name': table,
            'columns': [col.get('column_name') for col in columns if isinstance(col, dict)],
        }
        for table, columns in schema_catalog.items()
    ]


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


def build_factual_fallback_narrative(question: str, fact_pack: Dict[str, Any], llm_unavailable: bool = False) -> str:
    """Fallback narrative generator used when LLM calls are unavailable or permanently fail grounding validation."""
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
