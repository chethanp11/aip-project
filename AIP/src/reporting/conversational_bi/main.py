"""
Product 3: Conversational BI Assistant (Stateful Agentic AI)
Assigned Banking Agent: Conversational BI Agent
"""

import html
import json
from typing import Dict, Any, List
from shared.intelligence import invoke_capability, call_llm
from shared.lms import get_lms_table


async def _safe_invoke_capability(name: str, input_params: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a capability without letting optional infra outages fail the BI chat."""
    try:
        result = await invoke_capability(name, input_params)
        return result if isinstance(result, dict) else {}
    except Exception as exc:
        print(f"[Workflow: Reporting - Conversational BI] Capability '{name}' unavailable: {str(exc)}")
        return {}


def _safe_lms_table(table_name: str):
    """Read LMS data when infra is available; return an empty set otherwise."""
    try:
        return get_lms_table(table_name)
    except Exception as exc:
        print(f"[Workflow: Reporting - Conversational BI] LMS table '{table_name}' unavailable: {str(exc)}")
        return []


def _format_currency(value: float) -> str:
    """Format large banking amounts for executive visual summaries."""
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
        visual_focus = 'HQLA coverage and branch funding distribution'
    elif any(term in q_lower for term in ('branch', 'performance', 'deposit', 'balance')):
        visual_title = 'Branch Performance View'
        visual_focus = 'Balance concentration across available LMS branch records'
    elif any(term in q_lower for term in ('loan', 'risk', 'default', 'npl')):
        visual_title = 'Credit Exposure View'
        visual_focus = 'Available balance and liquidity context for credit discussion'
    else:
        visual_title = 'Executive BI Snapshot'
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
        branch_html = '<div class="convbi-empty">No branch records available for this access profile.</div>'

    buffer_html = ''.join(
        bar_row({**row, 'label': f"{row['label']} • {row['yield']:.2f}% yield"}, max_buffer, 'buffer')
        for row in buffer_rows
    )
    if not buffer_html:
        buffer_html = '<div class="convbi-empty">No liquidity buffer records available for this access profile.</div>'

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
    print(f'[Workflow: Reporting - Conversational BI] Answering banking analytics query: "{question}"')

    # 1. Gather KMS context mapping
    retrieve_result = await _safe_invoke_capability('knowledge_retrieval', {'question': question})
    
    # 2. Fetch live data from LMS tables
    deposits = _safe_lms_table('deposits')
    loans = _safe_lms_table('loans')
    buffers = _safe_lms_table('liquidity_buffers')
    performance = _safe_lms_table('branch_performance')
    
    lms_data_summary = json.dumps({
        'deposits': deposits,
        'loans': loans,
        'buffers': buffers,
        'performance': performance
    })
    visual_html = _build_conversation_visual_html(question, deposits, loans, buffers, performance, retrieve_result)

    # 3. Draft AI prompts linking Report context, LMS Database, and KMS
    system_prompt = """You are a professional Banking Executive BI Assistant. Your sole objective is to answer conversational analytical queries.
You must ground your calculations and answers strictly in the central KMS metrics configurations and the live LMS Database records.
Answer the question concisely in clean Markdown. Include inline tables, bullet points, and calculations if necessary.
Avoid guessing. Cite specific branches (North Plaza, Metro Hub, South Bay, West Valley) or HQLA categories based on actual LMS details."""

    user_prompt = f"""Analyst Query: "{question}"
KMS Semantics Definitions matched: {retrieve_result.get('context', '')}
Live LMS Database Records: {lms_data_summary}

Provide a comprehensive, executive-grade analysis response."""

    response_narrative = ''
    ai_answer = await call_llm(system_prompt, user_prompt)
    
    if ai_answer:
        response_narrative = ai_answer
        print('[Workflow: Reporting - Conversational BI] Live OpenAI BI response generated successfully.')
    else:
        print('[Workflow: Reporting - Conversational BI] OpenAI API call failed or key offline. Returning connection error.')
        response_narrative = (
            "## ⚠️ Unable to Connect to AI\n\n"
            "We are currently unable to connect to the AI service to process your request. "
            "Please check that your live `OPENAI_API_KEY` is correctly configured and authorized in `AIP-Infra/secrets/.env`."
        )

    # Generate the line spec to visualize the trend
    viz_spec = None
    if ai_answer:
        q_lower = question.lower()
        selected_trends = [3.12, 3.08, 3.15, 2.95, 2.88, 2.82, 2.65]
        if 'npl' in q_lower or 'default' in q_lower:
            selected_trends = [1.42, 1.45, 1.38, 1.49, 1.55, 1.62, 1.85]
        elif 'ldr' in q_lower or 'deposit' in q_lower:
            selected_trends = [78.5, 79.2, 80.5, 81.2, 80.8, 82.5, 85.8]
        elif 'cac' in q_lower or 'card' in q_lower:
            selected_trends = [180, 175, 192, 185, 178, 172, 215]

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
