"""
Product 3: Conversational BI Assistant (Stateful Agentic AI)
Assigned Enterprise Agent: Conversational BI Agent
"""

import html
import json
from typing import Dict, Any, List
from shared.intelligence import invoke_capability
from src.shared.infra.analytics_client import AnalyticsClient

_analytics_client = AnalyticsClient()
run_data_query = _analytics_client.run_compatible_read_query


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


def _build_live_fact_pack(question: str) -> Dict[str, Any]:
    """Build all Conv BI factual inputs from live analytics SQL only."""
    branch_balances = _safe_data_query("""
        SELECT branch, currency, SUM(balance) AS balance
        FROM accounts
        GROUP BY branch, currency
        ORDER BY branch, currency;
    """)
    deposit_balances = _safe_data_query("""
        SELECT branch, currency, SUM(balance) AS balance
        FROM accounts
        WHERE account_type ILIKE '%current%'
           OR account_type ILIKE '%sweeper%'
           OR account_type ILIKE '%deposit%'
        GROUP BY branch, currency
        ORDER BY branch, currency;
    """)
    loan_balances = _safe_data_query("""
        SELECT branch, currency, SUM(balance) AS balance
        FROM accounts
        WHERE account_type ILIKE '%loan%'
        GROUP BY branch, currency
        ORDER BY branch, currency;
    """)
    buffer_rows = _safe_data_query("""
        SELECT asset_type,
               SUM(amount) AS amount,
               AVG(haircut_percentage) AS haircut_percentage,
               AVG(yield_rate) AS yield_rate
        FROM liquidity_buffers
        GROUP BY asset_type
        ORDER BY amount DESC;
    """)
    account_type_totals = _safe_data_query("""
        SELECT account_type, currency, SUM(balance) AS balance
        FROM accounts
        GROUP BY account_type, currency
        ORDER BY account_type, currency;
    """)

    return {
        "fact_source_rule": "All numeric facts in the answer must come only from these live SQL query results.",
        "question": question,
        "branch_balances_by_currency": branch_balances,
        "deposit_balances_by_currency": deposit_balances,
        "loan_balances_by_currency": loan_balances,
        "liquidity_buffers": buffer_rows,
        "account_type_totals_by_currency": account_type_totals,
        "unavailable_facts": [
            label for label, rows in [
                ("loan_balances_by_currency", loan_balances),
                ("liquidity_buffers", buffer_rows),
                ("deposit_balances_by_currency", deposit_balances),
            ] if not rows
        ],
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


def _build_factual_narrative(question: str, fact_pack: Dict[str, Any]) -> str:
    """Render Conv BI answer from SQL facts only; KMS context is intentionally excluded."""
    unavailable = fact_pack.get("unavailable_facts") or []
    sections = [
        "## Data-grounded BI Response",
        "All factual values below are calculated from live Enterprise Ledger queries. KMS context is used only to guide topic selection and is not used as a source of facts.",
        "### Branch Balances by Currency",
        _markdown_balance_table(fact_pack.get("branch_balances_by_currency", [])),
        "### Deposit Balances by Currency",
        _markdown_balance_table(fact_pack.get("deposit_balances_by_currency", [])),
        "### Loan Balances by Currency",
        _markdown_balance_table(fact_pack.get("loan_balances_by_currency", [])),
        "### Liquidity Buffers",
        _markdown_buffer_table(fact_pack.get("liquidity_buffers", [])),
    ]
    if unavailable:
        sections.extend([
            "### Data Availability Notes",
            "\n".join(f"- `{item}` was not available from the authorized data source." for item in unavailable),
        ])
    return "\n\n".join(sections)


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

    # 2. Build live facts only from Enterprise Ledger queries.
    fact_pack = _build_live_fact_pack(question)
    visual_branch_rows = [
        {'branch': row.get('branch'), 'balance': _numeric(row, 'balance')}
        for row in fact_pack['branch_balances_by_currency']
    ]
    visual_buffers = [
        {
            'asset_type': row.get('asset_type'),
            'amount': _numeric(row, 'amount'),
            'yield_rate': _numeric(row, 'yield_rate'),
        }
        for row in fact_pack['liquidity_buffers']
    ]
    visual_html = _build_conversation_visual_html(
        question,
        deposits=[],
        loans=[],
        buffers=visual_buffers,
        performance=visual_branch_rows,
        retrieve_result=retrieve_result,
    )

    # 3. Render factual narrative deterministically so numeric values cannot leak from KMS context.
    response_narrative = _build_factual_narrative(question, fact_pack)
    ai_answer = response_narrative

    # Generate the line spec to visualize the trend dynamically from live Enterprise Ledger database records (no hardcoded fallback data)
    viz_spec = None
    if ai_answer:
        q_lower = question.lower()
        if 'npl' in q_lower or 'default' in q_lower:
            rows = _safe_data_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions WHERE direction = 'Outflow' GROUP BY month ORDER BY month DESC LIMIT 7;")
            selected_trends = [round(float(r['total']) / 100_000_000, 2) for r in reversed(rows)]
        elif 'ldr' in q_lower or 'deposit' in q_lower:
            rows = _safe_data_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions GROUP BY month ORDER BY month DESC LIMIT 7;")
            selected_trends = [round(float(r['total']) / 10_000_000, 1) for r in reversed(rows)]
        elif 'cac' in q_lower or 'card' in q_lower:
            rows = _safe_data_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions WHERE transaction_type = 'Sweep Transfer' GROUP BY month ORDER BY month DESC LIMIT 7;")
            selected_trends = [round(float(r['total']) / 2_000_000, 0) for r in reversed(rows)]
        else:
            rows = _safe_data_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions GROUP BY month ORDER BY month DESC LIMIT 7;")
            selected_trends = [round(float(r['total']) / 200_000_000, 2) for r in reversed(rows)]

        selected_trends = selected_trends[:7]

        if selected_trends:
            viz_result = await _safe_invoke_capability('visualization', {
                'chartType': 'line',
                'trends': selected_trends
            })
            viz_spec = viz_result.get('vegaSpec')

    return {
        'narrative': response_narrative,
        'visualHtml': visual_html,
        'vegaSpec': viz_spec
    }
