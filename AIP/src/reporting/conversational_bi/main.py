"""
Product 3: Conversational BI Assistant (Stateful Agentic AI)
Assigned Enterprise Agent: Conversational BI Agent
"""

import html
import json
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


def _schema_catalog() -> Dict[str, Any]:
    """Discover only tables and columns authorized for the active profile."""
    tables = _analytics_client.list_tables()
    catalog: Dict[str, Any] = {}
    for table in tables:
        try:
            catalog[table] = _analytics_client.get_table_schema(table)
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
        referenced = set(__import__('re').findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', sql.lower())) & {t.lower() for t in allowed_tables}
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
    q_words = {w for w in __import__('re').findall(r'[a-zA-Z_]+', question.lower()) if len(w) > 2}
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


async def _build_live_fact_pack(question: str, retrieve_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build Conv BI facts dynamically from authorized schema and question-specific SQL."""
    schema_catalog = _schema_catalog()
    query_plan = await _generate_query_plan(question, schema_catalog, retrieve_result)
    query_results: List[Dict[str, Any]] = []
    for planned in query_plan:
        rows = _safe_custom_query(planned['sql'])
        query_results.append({
            'label': planned['label'],
            'sql': planned['sql'],
            'rows': rows,
            'row_count': len(rows),
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
    intro = "Live AI narrative generation is unavailable, so this fallback view is rendered from authorized live SQL query results. KMS context is not used as a source of facts."
    if not llm_unavailable:
        intro = "All factual values below are calculated from authorized live SQL query results."
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

    # 2. Dynamically inspect authorized schema and build question-specific live facts.
    fact_pack = await _build_live_fact_pack(question, retrieve_result)
    # 3. Ask the LLM to write the BI narrative using only live SQL facts; fallback remains deterministic.
    response_narrative = await _build_llm_narrative(question, fact_pack, retrieve_result)
    ai_answer = response_narrative

    # Generate the line spec to visualize the trend dynamically from live Enterprise Ledger database records (no hardcoded fallback data)
    viz_spec = None
    if ai_answer:
        q_lower = question.lower()
        if 'npl' in q_lower or 'default' in q_lower:
            rows = _safe_custom_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions WHERE direction = 'Outflow' GROUP BY month ORDER BY month DESC LIMIT 7")
            selected_trends = [round(float(r['total']) / 100_000_000, 2) for r in reversed(rows)]
        elif 'ldr' in q_lower or 'deposit' in q_lower:
            rows = _safe_custom_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions GROUP BY month ORDER BY month DESC LIMIT 7")
            selected_trends = [round(float(r['total']) / 10_000_000, 1) for r in reversed(rows)]
        elif 'cac' in q_lower or 'card' in q_lower:
            rows = _safe_custom_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions WHERE transaction_type = 'Sweep Transfer' GROUP BY month ORDER BY month DESC LIMIT 7")
            selected_trends = [round(float(r['total']) / 2_000_000, 0) for r in reversed(rows)]
        else:
            rows = _safe_custom_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions GROUP BY month ORDER BY month DESC LIMIT 7")
            selected_trends = [round(float(r['total']) / 200_000_000, 2) for r in reversed(rows)]

        selected_trends = selected_trends[:7]

        if selected_trends:
            viz_result = await _safe_invoke_capability('visualization', {
                'chartType': 'line',
                'trends': selected_trends
            })
            viz_spec = viz_result.get('vegaSpec')

    visual_decision = await _decide_visual_representation(question, fact_pack)
    dynamic_visual_html = _build_dynamic_visual_html(question, fact_pack, visual_decision)
    narrative_html = _markdown_to_html(response_narrative)
    rendered_html = narrative_html + dynamic_visual_html

    return {
        'narrative': response_narrative,
        'renderedHtml': rendered_html,
        'visualDecision': visual_decision,
        'visualHtml': dynamic_visual_html,
        'vegaSpec': viz_spec
    }
