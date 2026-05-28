"""
Summarization Capability
"""

import re
from typing import Dict, Any
from src.shared.intelligence import call_llm

config = {
    'description': 'Compresses large paragraphs, logs, or analysis outputs into high-density bullet summaries.',
    'inputSchema': {
        'text': 'string',
        'prompt': 'string'
    },
    'outputSchema': {
        'summary': 'string'
    }
}

async def handler(input_params: Dict[str, Any]) -> Dict[str, Any]:
    raw_text = input_params.get('text', '') or ''
    prompt = input_params.get('prompt', '') or ''
    if not raw_text.strip():
        return {'summary': 'No text provided to summarize.'}

    # Attempt live LLM summary if key is available
    system_prompt = "You are a professional banking systems analyst. Summarize the provided logs or analysis outputs into precise, high-density bulleted key takeaways."
    if prompt:
        system_prompt += f" Adhere strictly to these user directives: {prompt}"
        
    ai_summary = await call_llm(system_prompt, raw_text)
    if ai_summary:
        return {'summary': ai_summary.strip()}

    # Fallback: Extract sentences and build bullet list
    sentences = [s.strip() for s in re.split(r'[.!\n]+', raw_text) if s.strip()]
    sentences = [s for s in sentences if len(s) > 5]
    key_takeaways = [f"• {s}." for s in sentences[:3]]

    if key_takeaways:
        return {'summary': '\n'.join(key_takeaways)}
    else:
        return {'summary': '• Insufficient text length to generate structural bullet summary.'}
