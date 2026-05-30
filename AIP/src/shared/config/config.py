"""
Centralized Configuration Module for AIM Intelligence Platform (AIP)
Loads env variables from the root .env file and standardizes all database and path mappings.
"""

import os
from dotenv import load_dotenv

# Find the workspace root or external secrets .env file
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
env_path = os.path.join(base_dir, 'AIP-Infra', 'secrets', '.env')

# Fallback: check workspace root or current directory
if not os.path.exists(env_path):
    env_path = os.path.join(base_dir, '.env')

if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# PostgreSQL Credentials
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5433))
POSTGRES_DB = os.getenv("POSTGRES_DB", "treasurydb")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Central Repository PostgreSQL Credentials
AIP_POSTGRES_HOST = os.getenv("AIP_POSTGRES_HOST", "localhost")
AIP_POSTGRES_PORT = int(os.getenv("AIP_POSTGRES_PORT", 5432))
AIP_POSTGRES_DB = os.getenv("AIP_POSTGRES_DB", "aipdb")
AIP_POSTGRES_USER = os.getenv("AIP_POSTGRES_USER")
AIP_POSTGRES_PASSWORD = os.getenv("AIP_POSTGRES_PASSWORD")

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# External AIP-Infra storage and logging mappings.
INFRA_ROOT = os.path.abspath(os.path.join(base_dir, "AIP-Infra"))
STORAGE_ROOT = os.path.join(INFRA_ROOT, "storage")
KMS_ROOT = os.path.join(INFRA_ROOT, "kms")
REPORT_PATH = os.path.join(STORAGE_ROOT, "reports")
ARTIFACT_PATH = os.path.join(STORAGE_ROOT, "artifacts")
ARCHIVE_PATH = os.path.join(STORAGE_ROOT, "archives")
LOG_PATH = os.path.join(INFRA_ROOT, "logs")
CHATS_PATH = os.path.join(STORAGE_ROOT, "chats")

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
    """Return a shared workspace KMS folder path under AIP-Infra/kms."""
    safe_team = "".join(ch for ch in (team or "General") if ch.isalnum() or ch in ("_", "-"))
    return os.path.join(KMS_ROOT, safe_team)

def get_kms_team_runtime_path(team: str) -> str:
    """Return a workspace-specific KMS runtime folder."""
    return os.path.join(get_kms_team_path(team), "runtime")

# Ensure external paths exist
for path in [REPORT_PATH, ARTIFACT_PATH, ARCHIVE_PATH, LOG_PATH, KMS_ROOT, CHATS_PATH]:
    if path:
        os.makedirs(path, exist_ok=True)

for team in ["Treasury", "Compliance", "Wealth", "Credit"]:
    for path in [
        get_kms_team_path(team),
        os.path.join(get_kms_team_path(team), "context"),
        get_kms_team_runtime_path(team),
    ]:
        os.makedirs(path, exist_ok=True)
