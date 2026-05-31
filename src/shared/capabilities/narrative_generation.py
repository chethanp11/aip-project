"""
Narrative Generation Capability
"""

import json
import os
from typing import Dict, Any
from src.shared.config import config as app_config

config = {
    'description': 'Formats metrics variables and text summaries into standard Markdown templates from the KMS.',
    'inputSchema': {
        'templateId': 'string',
        'variables': 'object'
    },
    'outputSchema': {
        'narrative': 'string'
    }
}

def handler(input_params: Dict[str, Any]) -> Dict[str, Any]:
    template_id = input_params.get('templateId', 'briefing_brief') or 'briefing_brief'
    variables = input_params.get('variables', {}) or {}
    
    # Fetch template structure dynamically from the local database
    template_structure = "# Performance Briefing\n\nMetric Value: :metricValue\nSummary: :summaryText"
    try:
        from src.kms.index import get_postgres_db
        conn = get_postgres_db()
        cursor = conn.cursor()
        cursor.execute("SELECT structure FROM analytical_templates WHERE id = ?;", (template_id,))
        row = cursor.fetchone()
        if row:
            template_structure = row['structure']
    except Exception as e:
        print(f"[Narrative Cap Error] Database templates query failed: {str(e)}")

    # Replace keys in template with variables
    narrative = template_structure
    for key, val in variables.items():
        placeholder = f":{key}"
        narrative = narrative.replace(placeholder, str(val))
        
    return {
        'narrative': narrative
    }
