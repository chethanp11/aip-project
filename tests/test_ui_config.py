"""
Integration tests for UI Configurations API (GET and POST /api/v1/ui/config).
"""

import os
import sys
import pytest

# Ensure AIP/ is current working directory so relative operations resolve correctly
aip_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../AIP"))
original_cwd = os.getcwd()
os.chdir(aip_root)

# Ensure AIP/ and src/ are in path
sys.path.insert(0, aip_root)
sys.path.insert(0, os.path.join(aip_root, "src"))

from fastapi.testclient import TestClient
from src.main import app
from shared.session import set_session

def test_get_ui_config():
    """Verifies that dynamic GET /api/v1/ui/config returns seeded persona configs."""
    # Reset table UI configurations to clean defaults
    from src.kms.index import get_postgres_db
    import json
    conn = get_postgres_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ui_configurations;")
    cursor.executemany("INSERT INTO ui_configurations VALUES (?, ?, ?);", [
        ("Business User",
         "home,reporting,analytics,db-explorer",
         json.dumps({
             "reporting": ["bi", "proactive"],
             "analytics": ["discovery", "rca", "whatif", "narratives"],
             "automation": [],
             "data-science": []
         })),
        ("Analytics Professional",
         "home,reporting,data-science,db-explorer",
         json.dumps({
             "reporting": ["prism", "builder"],
             "analytics": [],
             "automation": [],
             "data-science": ["prep", "develop", "document", "pulse"]
         })),
        ("Business Admin",
         "home,reporting,analytics,automation,data-science,kms,db-explorer,ui-config",
         json.dumps({
             "reporting": ["prism", "builder", "bi", "proactive"],
             "analytics": ["discovery", "rca", "whatif", "narratives"],
             "automation": ["design", "orchestration", "approvals", "monitor"],
             "data-science": ["prep", "develop", "document", "pulse"]
         }))
    ])
    conn.commit()

    client = TestClient(app)
    
    # Establish active session
    token = "AIP-USER-SESSION-TESTGET1"
    set_session(token, {
        'username': 'Treasury_User',
        'role': 'Business User',
        'clearance': 'Internal',
        'display_name': 'Treasury Business User'
    })
    
    response = client.get("/api/v1/ui/config", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    configs = response.json()
    
    # Assert standard categories are present
    assert "Business User" in configs
    assert "Analytics Professional" in configs
    assert "Business Admin" in configs
    
    # Check default presets
    assert "home" in configs["Business User"]["visible_suites"]
    assert "reporting" in configs["Business User"]["visible_suites"]
    assert "analytics" in configs["Business User"]["visible_suites"]
    
    assert "bi" in configs["Business User"]["visible_subproducts"]["reporting"]
    assert "proactive" in configs["Business User"]["visible_subproducts"]["reporting"]
    assert "prism" not in configs["Business User"]["visible_subproducts"]["reporting"]

def test_post_ui_config_admin_success():
    """Verifies that an SME (Business Admin) can successfully write/update configurations."""
    client = TestClient(app)
    
    token = "AIP-SME-SESSION-TESTPOST1"
    set_session(token, {
        'username': 'Treasury_SME',
        'role': 'SME',
        'clearance': 'Confidential',
        'display_name': 'Treasury SME'
    })
    
    payload = {
        "category": "Test Persona",
        "visible_suites": "home,reporting,analytics,db-explorer,kms",
        "visible_subproducts": {
            "reporting": ["bi", "proactive", "prism"],
            "analytics": ["discovery", "rca"]
        }
    }
      
    response = client.post("/api/v1/ui/config", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Verify the update works on subsequent GET
    get_res = client.get("/api/v1/ui/config", headers={"Authorization": f"Bearer {token}"})
    configs = get_res.json()
    assert "Test Persona" in configs
    assert "kms" in configs["Test Persona"]["visible_suites"]
    assert "prism" in configs["Test Persona"]["visible_subproducts"]["reporting"]

def test_post_ui_config_non_admin_forbidden():
    """Verifies that non-admin (SME) users are forbidden from posting config updates (RBAC checks)."""
    client = TestClient(app)
    
    # Token for a normal Analyst
    token = "AIP-ANALYST-SESSION-TESTPOST1"
    set_session(token, {
        'username': 'Treasury_Analyst',
        'role': 'Analyst',
        'clearance': 'Internal',
        'display_name': 'Treasury Analyst'
    })
    
    payload = {
        "category": "Test Persona",
        "visible_suites": "home",
        "visible_subproducts": {}
    }
    
    response = client.post("/api/v1/ui/config", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]
    
    # Clean up working directory context
    os.chdir(original_cwd)

def test_dynamic_user_login():
    """Verifies that user/password dynamically intercepts and overrides role/allowed context."""
    client = TestClient(app)
    
    # 1. Login as compliance user persona
    payload = {
        "username": "user",
        "password": "password",
        "lob": "Compliance",
        "category": "Analytics Professional"
    }
    
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["role"] == "Analyst"
    assert data["displayName"] == "Compliance Analyst"
    
    # 2. Try with business admin / Treasury LOB
    payload = {
        "username": "user",
        "password": "password",
        "lob": "Treasury",
        "category": "Business Admin"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["role"] == "SME"
    assert data["displayName"] == "Treasury SME"
