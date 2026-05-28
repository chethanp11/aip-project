"""
KMS Retrieval Agent definition using LangGraph.
"""

from src.shared.tools.kms_tool import retrieve_kms_knowledge

SYSTEM_INSTRUCTIONS = """
You are a KMS Retrieval Agent.
Your goal is to retrieve relevant metrics vocabulary, definitions, glossaries, and business metadata from the Knowledge Management System (KMS).
Use the retrieve_kms_knowledge tool with the user's natural language question.
Do not make assumptions or invent definitions. Return the raw KMS results clearly.
""".strip()

def get_tools():
    return [retrieve_kms_knowledge]
