"""
Centralized Configuration Module for AIM Intelligence Platform (AIP)
Loads env variables from the root .env file and standardizes all database and path mappings.
"""

import os
from dotenv import load_dotenv

# Find the workspace root or external secrets .env file
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
env_path = os.path.join(base_dir, 'Infra', 'secrets', '.env')

# Fallback: check workspace root or current directory
if not os.path.exists(env_path):
    env_path = os.path.join(base_dir, '.env')

if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# SQLite Credentials
SQLITE_DB = os.getenv("SQLITE_DB", "treasurydb")

# GRAPHDB Configuration
GRAPHDB_URI = os.getenv("GRAPHDB_URI", "bolt://localhost:7687")
GRAPHDB_USER = os.getenv("GRAPHDB_USER", "graphdb")
GRAPHDB_PASSWORD = os.getenv("GRAPHDB_PASSWORD", "password123")

# External Infra storage and logging mappings.
INFRA_ROOT = os.path.abspath(os.path.join(base_dir, "Infra"))
STORAGE_ROOT = os.path.join(INFRA_ROOT, "storage")
KMS_ROOT = os.path.join(INFRA_ROOT, "kms")
REPORT_PATH = os.path.join(STORAGE_ROOT, "reports")
ARTIFACT_PATH = os.path.join(STORAGE_ROOT, "artifacts")
ARCHIVE_PATH = os.path.join(STORAGE_ROOT, "archives")
LOG_PATH = os.path.join(INFRA_ROOT, "logs")
CHATS_PATH = os.path.join(STORAGE_ROOT, "chats")
ALERTS_PATH = os.path.join(STORAGE_ROOT, "alerts")
SHARED_REPORT_PATH = REPORT_PATH

def resolve_kms_team(username: str, allowed_domains: list[str] | None = None) -> str:
    """Resolve Analyst/SME usernames and domain grants to a shared business team folder."""
    normalized = (username or "").lower()
    if "treasury" in normalized:
        return "Treasury"
    if "compliance" in normalized:
        return "Compliance"
    if "wealth" in normalized:
        return "Wealth"
    if "credit" in normalized:
        return "Credit"

    domains = ",".join(allowed_domains or []).lower()
    if "treasury" in domains or "cash management" in domains:
        return "Treasury"
    if "compliance" in domains or "controls" in domains:
        return "Compliance"
    if "wealth" in domains or "advisory" in domains or "investment" in domains:
        return "Wealth"
    if "credit" in domains:
        return "Credit"
    return "General"

def get_kms_team_path(team: str) -> str:
    """Return a shared workspace KMS folder path under Infra/kms."""
    safe_team = "".join(ch for ch in (team or "General") if ch.isalnum() or ch in ("_", "-"))
    return os.path.join(KMS_ROOT, safe_team)

def get_kms_team_runtime_path(team: str) -> str:
    """Return a workspace-specific KMS runtime folder."""
    return os.path.join(get_kms_team_path(team), "runtime")

# Ensure external paths exist
for path in [REPORT_PATH, ARTIFACT_PATH, ARCHIVE_PATH, LOG_PATH, KMS_ROOT, CHATS_PATH, ALERTS_PATH]:
    if path:
        os.makedirs(path, exist_ok=True)

for team in ["Treasury", "Compliance", "Wealth", "Credit"]:
    for path in [
        get_kms_team_path(team),
        os.path.join(get_kms_team_path(team), "context"),
        get_kms_team_runtime_path(team),
    ]:
        os.makedirs(path, exist_ok=True)
