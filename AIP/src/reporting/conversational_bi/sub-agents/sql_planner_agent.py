"""
SQL Planner Agent definition using google-antigravity SDK.
"""

from google.antigravity import Agent, LocalAgentConfig
from src.shared.tools.database_tool import get_database_schema

SYSTEM_INSTRUCTIONS = """
You are a PostgreSQL BI query planner.
Your goal is to generate at most 6 read-only SELECT queries that will retrieve the factual data needed to answer the user's question.
You must retrieve the database schema using the get_database_schema tool first.
Use ONLY tables and columns listed in the retrieved schema. Do not guess or invent columns.
Never write multiple statements, or modify data (INSERT, UPDATE, DELETE, etc.). Enforce read-only statements.
Return JSON ONLY, matching this shape:
{"queries": [{"label": "short business label", "sql": "SELECT ..."}]}
""".strip()

def get_sql_planner_agent() -> Agent:
    config = LocalAgentConfig(
        tools=[get_database_schema],
        system_instructions=SYSTEM_INSTRUCTIONS
    )
    return Agent(config=config)
