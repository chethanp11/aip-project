"""
Product 8: Business Narratives Storytelling (Stateful Agentic AI)
Assigned Enterprise Agent: Narrative Storyteller Agent
"""

from typing import Dict, Any
from shared.intelligence import invoke_capability, call_llm
from shared.session import get_profile_context_defaults

async def run_business_narratives_workflow(channel: str, metric_name: str, value: str, growth_rate: str, primary_driver: str, prompt: str = "") -> Dict[str, Any]:
    print(f"[Workflow: Analytics - Narratives] Compiling stories for channel: {channel}")

    system_prompt = f"""You are an expert Chief Communications Officer for a tier-1 enterprise organization.
Your objective is to compile an stakeholder analysis copy for the target channel ({channel.upper()}).
Keep your tone highly professional, precise, and authoritative. Highlight the driver ({primary_driver}) and performance variance."""

    user_prompt = f"""Synthesize a narrative summary report:
- Target channel: {channel}
- Audited Metric Name: {metric_name}
- Metric Value: {value}
- Growth Rate: {growth_rate}% MoM
- Primary Asset Driver: {primary_driver}"""
    if prompt:
        user_prompt += f"\n- Additional Analyst Directives: {prompt}"
    user_prompt += "\nEnsure it includes appropriate markdown elements matching enterprise presentation standards."

    tailored_narrative = ''
    ai_narrative = await call_llm(system_prompt, user_prompt)
    
    if ai_narrative:
        tailored_narrative = ai_narrative
        print('[Workflow: Analytics - Narratives] Live OpenAI stakeholder story generated successfully.')
    else:
        print('[Workflow: Analytics - Narratives] OpenAI key offline, using local templates.')
        
        try:
            val_f = float(value)
            growth_f = float(growth_rate)
            compare_val = str(round(val_f / (1.0 + growth_f / 100.0), 3))
        except:
            compare_val = "0.0"
            
        # Dynamically fetch profile default formula and context parameters
        user_defaults = get_profile_context_defaults()
        formula = user_defaults.get('metricFormula', 'net_interest_margin')
        cc_group = user_defaults.get('channel', '#general-alerts').replace('#', '').replace('-alerts', '')

        variables = {
            'metricName': metric_name,
            'metricValue': value,
            'compareValue': compare_val,
            'metricFormula': formula,
            'explanation': f"Root cause drivers analysis isolated the core factor behind performance shift to be: {primary_driver}. Growth computed at {growth_rate}% in the latest cycle.",
            'summaryText': f"Enterprise narrative brief synthesized automatically for target channel: {channel.upper()}."
        }

        generation = await invoke_capability('narrative_generation', {
            'templateId': 'briefing_brief',
            'variables': variables
        })

        tailored_narrative = generation.get('narrative', '')
        
        # Format explicitly by channel for offline fallbacks
        c_lower = channel.lower()
        if c_lower == 'slack':
            tailored_narrative = f"🚨 *AIP System Alert: {metric_name}* 🚨\n\nLatest evaluated status: *{value}* (growth: *{growth_rate}% MoM*).\n\n*Key Diagnostics:* {variables['explanation']}\n\n_CC: @{cc_group}-committee_"
        elif c_lower == 'board':
            tailored_narrative = f"# Stakeholder Review: {metric_name}\n\n## 📝 Performance and Metrics Review\nDuring this evaluation period, **{metric_name}** registered **{value}**, reflecting a **{growth_rate}% MoM** transition.\n\n## 📊 Segment Performance Diagnostics\n* Primary variance driver was identified in: **{primary_driver}**.\n* Calculation models align directly to governance standards and KMS definitions."

    return {
        'channel': channel,
        'narrative': tailored_narrative
    }
