"""
AIP In-Memory Session Manager
"""

import time
from typing import Dict, Any
from src.shared.infra_client.analytics_client import AnalyticsClient

_analytics_client = AnalyticsClient()
run_sqlite_query = _analytics_client.run_compatible_read_query

active_sessions: Dict[str, Dict[str, Any]] = {}

def get_session(session_id: str) -> Dict[str, Any]:
    """Retrieves or creates a session by ID."""
    if session_id not in active_sessions:
        active_sessions[session_id] = {
            'id': session_id,
            'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'filters': {'period': 'Q1-2026'}
        }
    return active_sessions[session_id]

def set_session(session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Updates and saves a session payload."""
    session = get_session(session_id)
    session.update(payload)
    session['updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    active_sessions[session_id] = session
    return session

def clear_session(session_id: str) -> bool:
    """Removes an active session."""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return True
    return False

def get_profile_context_defaults() -> Dict[str, Any]:
    """Dynamically maps operational defaults matching the active logged-in Analyst/SME profile domain context."""
    from shared.intelligence import active_agent_context
    active_ctx = active_agent_context.get()
    api_key = active_ctx.get('api_key', '') if active_ctx else ''

    # Dynamically compute metrics from live database
    try:
        # 1. LDR
        acc_sums = run_sqlite_query("SELECT account_type, SUM(balance) as total FROM accounts GROUP BY account_type;")
        deposits = 0.0
        loans = 0.0
        for row in acc_sums:
            act = row['account_type']
            val = float(row['total'])
            if act in ("Corporate Current", "Treasury Sweeper", "Operating Current", "Resource Sweeper"):
                deposits += val
            elif act == "Yield Earning Deposit":
                loans += val
        ldr_val = round((loans / deposits * 100) if deposits else 85.8, 2)

        # 2. NPL
        risk_avg = run_sqlite_query("SELECT AVG(risk_score) as avg_risk FROM corporate_clients;")
        npl_val = round(float(risk_avg[0]['avg_risk']) if risk_avg and risk_avg[0]['avg_risk'] else 1.85, 2)

        # 3. LCR
        buffers = run_sqlite_query("SELECT SUM(amount * (1.0 - haircut_percentage / 100.0)) as hqla FROM liquidity_buffers;")
        hqla = float(buffers[0]['hqla']) if buffers and buffers[0]['hqla'] else 1075000000.0
        outflows = run_sqlite_query("SELECT SUM(amount) as total FROM transactions WHERE direction = 'Outflow';")
        outflow_val = float(outflows[0]['total']) if outflows and outflows[0]['total'] else 80000000.0
        lcr_val = round((hqla / outflow_val * 10.0) if outflow_val else 114.5, 2)

        # 4. PSI
        tx_count = run_sqlite_query("SELECT COUNT(*) as cnt FROM transactions;")
        cnt = tx_count[0]['cnt'] if tx_count else 1050
        psi_val = round(float(cnt) / 5000.0, 2)

        # Fetch trends dynamically
        rows = run_sqlite_query("SELECT LEFT(timestamp, 7) as month, SUM(amount) as total FROM transactions GROUP BY month ORDER BY month DESC LIMIT 7;")
        db_trends = [round(float(r['total']) / 10_000_000, 1) for r in reversed(rows)]
        while len(db_trends) < 7:
            db_trends.append(round(1.5 + len(db_trends) * 0.2, 2))
        db_trends = db_trends[:7]
    except Exception as e:
        print(f"[Defaults Dynamic Calculation Error] {e}")
        ldr_val, npl_val, lcr_val, psi_val = 85.8, 1.85, 114.5, 0.24
        db_trends = [1.0, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7]

    # Standard default (Operations/General fallback)
    defaults = {
        'metricId': 'npl_ratio',
        'metricName': 'Outcome Variance Risk Ratio',
        'metricValue': f"{npl_val}%",
        'compareValue': f"{round(npl_val * 0.8, 2)}%",
        'metricFormula': 'outcome_variance_risk_ratio',
        'trends': db_trends,
        'business_domain': 'Outcome Analytics',
        'sme': 'Marcus Vance',
        'channel': '#general-alerts'
    }

    if api_key in active_sessions:
        session = active_sessions[api_key]
        username = (session.get('username') or '').lower()

        if 'governance' in username:
            defaults.update({
                'metricId': 'lcr_ratio',
                'metricName': 'Operational Reserve Coverage (ORC)',
                'metricValue': f"{lcr_val}%",
                'compareValue': f"{round(lcr_val * 0.95, 2)}%",
                'metricFormula': 'operational_reserve_coverage',
                'trends': db_trends,
                'business_domain': 'Governance & Controls',
                'sme': 'Dr. Sarah Lin',
                'channel': '#governance-alerts'
            })
        elif 'insights' in username:
            defaults.update({
                'metricId': 'ldr_ratio',
                'metricName': 'Utilization-to-Baseline Ratio (UBR)',
                'metricValue': f"{ldr_val}%",
                'compareValue': f"{round(ldr_val * 0.96, 2)}%",
                'metricFormula': 'utilization_to_baseline_ratio',
                'trends': db_trends,
                'business_domain': 'Operational Resource Management',
                'sme': 'Dr. Sarah Lin',
                'channel': '#operational-resource-alerts'
            })
        elif 'operations' in username:
            defaults.update({
                'metricId': 'default_rate',
                'metricName': 'Portfolio Variance Risk Rate',
                'metricValue': f"{npl_val * 1.15}%",
                'compareValue': f"{round(npl_val, 2)}%",
                'metricFormula': 'portfolio_variance_risk_rate',
                'trends': db_trends,
                'business_domain': 'Operations Performance',
                'sme': 'Marcus Vance',
                'channel': '#risk-alerts'
            })
        elif 'modelops' in username or 'model' in username:
            defaults.update({
                'metricId': 'psi_metric',
                'metricName': 'Population Stability Index (PSI)',
                'metricValue': f"{psi_val}",
                'compareValue': "0.10",
                'metricFormula': 'population_stability_index',
                'trends': db_trends,
                'business_domain': 'Model Operations',
                'sme': 'Marcus Vance',
                'channel': '#model-pulse-alerts'
            })

    return defaults
