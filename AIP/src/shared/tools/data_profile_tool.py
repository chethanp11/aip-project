"""
PII Redaction and Data Column Distribution Profiler Tools.
"""

import re
from typing import Dict, Any, List

try:
    from src.shared.infra.analytics_client import AnalyticsClient
except ImportError:
    from shared.infra.analytics_client import AnalyticsClient

_analytics_client = AnalyticsClient()


def get_column_distribution_profile(table: str, column: str) -> Dict[str, Any]:
    """Generates basic cardinality, null-rate, and distribution profiles for a column.

    Args:
        table: The table name.
        column: The column name.

    Returns:
        A dictionary containing total rows, distinct values, null count, and null percentage.
    """
    # Sanitize inputs to prevent SQL injection in metadata queries
    table_clean = re.sub(r'[^a-zA-Z0-9_]', '', table)
    column_clean = re.sub(r'[^a-zA-Z0-9_]', '', column)
    
    if not table_clean or not column_clean:
        return {'error': 'Invalid table or column name.'}

    try:
        total_rows_res = _analytics_client.run_custom_query(f"SELECT COUNT(*) as count FROM {table_clean}")
        total_rows = int(total_rows_res[0].get('count', 0)) if total_rows_res else 0

        if total_rows == 0:
            return {'total_rows': 0, 'distinct_values': 0, 'null_count': 0, 'null_percentage': 0.0}

        null_rows_res = _analytics_client.run_custom_query(f"SELECT COUNT(*) as count FROM {table_clean} WHERE {column_clean} IS NULL")
        null_rows = int(null_rows_res[0].get('count', 0)) if null_rows_res else 0

        distinct_res = _analytics_client.run_custom_query(f"SELECT COUNT(DISTINCT {column_clean}) as count FROM {table_clean}")
        distinct_count = int(distinct_res[0].get('count', 0)) if distinct_res else 0

        return {
            'total_rows': total_rows,
            'distinct_values': distinct_count,
            'null_count': null_rows,
            'null_percentage': round((null_rows / total_rows) * 100, 2)
        }
    except Exception as exc:
        return {'error': str(exc)}


def redact_pii_and_sensitive_fields(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Automatically scans database result rows and redacts sensitive PII or unhashed fields.

    Args:
        rows: List of record dictionaries.

    Returns:
        Redacted list of record dictionaries.
    """
    if not rows:
        return []

    # Standard patterns for SSN, email, phone, credit card
    ssn_pattern = re.compile(r'^\d{3}-\d{2}-\d{4}$')
    email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
    phone_pattern = re.compile(r'^\+?1?\d{9,15}$')
    credit_card_pattern = re.compile(r'^\d{12,19}$')

    redacted_rows = []
    for r in rows:
        redacted_row = {}
        for col_name, val in r.items():
            col_lower = col_name.lower()
            
            # 1. Column name checks (mask password, ssn, pin, card, secret columns entirely)
            if any(term in col_lower for term in ('password', 'ssn', 'pin', 'secret', 'phone', 'email', 'card_number')):
                redacted_row[col_name] = "[REDACTED PII]"
                continue
                
            # 2. Value pattern matching checks for string fields
            if isinstance(val, str):
                val_clean = val.strip()
                if ssn_pattern.match(val_clean):
                    redacted_row[col_name] = "[REDACTED SSN]"
                elif email_pattern.match(val_clean):
                    redacted_row[col_name] = "[REDACTED EMAIL]"
                elif phone_pattern.match(val_clean):
                    redacted_row[col_name] = "[REDACTED PHONE]"
                elif credit_card_pattern.match(val_clean):
                    redacted_row[col_name] = "[REDACTED CARD]"
                else:
                    redacted_row[col_name] = val
            else:
                redacted_row[col_name] = val
                
        redacted_rows.append(redacted_row)
        
    return redacted_rows
