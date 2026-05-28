"""
SQL Debugger Agent definition using google-antigravity SDK.
"""

from google.antigravity import Agent, LocalAgentConfig
from src.shared.tools.database_tool import get_database_schema

SYSTEM_INSTRUCTIONS = """
You are an expert PostgreSQL DBA and SQL Debugger Agent.
Your goal is to repair a failing SQL query based on the database execution error and the authorized schema catalog.
First, fetch the authorized schema using the get_database_schema tool.
Generate a corrected, valid read-only PostgreSQL query that resolves the error and accurately answers the question.
Use only authorized schema tables and columns. Do not invent columns.
Do not use write operations (INSERT, UPDATE, DELETE, etc.). Enforce a read-only SELECT.
Return JSON ONLY matching this shape:
{"repaired_sql": "SELECT ..."}
""".strip()

def get_sql_debugger_agent() -> Agent:
    config = LocalAgentConfig(
        tools=[get_database_schema],
        system_instructions=SYSTEM_INSTRUCTIONS
    )
    return Agent(config=config)
