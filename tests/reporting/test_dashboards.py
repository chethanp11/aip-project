"""
Integration and unit tests for the Dashboard View functionality.
"""

import os
import sys
import pytest

aip_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
original_cwd = os.getcwd()
os.chdir(aip_root)

sys.path.insert(0, aip_root)
sys.path.insert(0, os.path.join(aip_root, "src"))

from fastapi.testclient import TestClient
from src.main import app
from shared.session import set_session
from src.shared.config import config
from src.business_suite.dashboards.main import get_dashboard_reports, seed_premium_reports_if_empty

def test_seeding_and_scanning():
    """Verifies that seeder adds reports and get_dashboard_reports scans correctly."""
    # Ensure reports exist by running seeder
    seed_premium_reports_if_empty()
    
    reports = get_dashboard_reports()
    assert len(reports) >= 3
    
    filenames = [r['filename'] for r in reports]
    assert "treasury_liquidity_report.html" in filenames
    assert "compliance_audit_summary.html" in filenames
    assert "wealth_investment_outlook.html" in filenames

def test_api_list_dashboard_reports():
    """Verifies GET /api/v1/dashboards/reports fetches metadata under authorization."""
    client = TestClient(app)
    
    # Establish authed session
    token = "AIP-TEST-DASHBOARD-TOKEN1"
    set_session(token, {
        'username': 'Treasury_Analyst',
        'role': 'Analyst',
        'clearance': 'Internal',
        'display_name': 'Treasury Analyst'
    })
    
    # Attempt unauthorized request
    response = client.get("/api/v1/dashboards/reports")
    assert response.status_code == 401
    
    # Authorized request
    response = client.get("/api/v1/dashboards/reports", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    reports = response.json()
    assert isinstance(reports, list)
    assert len(reports) >= 3

def test_api_get_dashboard_report_security():
    """Verifies that filename parameters are validated against directory traversal attacks."""
    client = TestClient(app)
    
    token = "AIP-TEST-DASHBOARD-TOKEN2"
    set_session(token, {
        'username': 'Treasury_Analyst',
        'role': 'Analyst',
        'clearance': 'Internal',
        'display_name': 'Treasury Analyst'
    })
    
    # Test directory traversal blocks
    response = client.get("/api/v1/dashboards/reports/..\\config.html", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert "Invalid filename" in response.json()["detail"]
    
    # Test extension block
    response = client.get("/api/v1/dashboards/reports/config.py", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert "Only HTML files are allowed" in response.json()["detail"]
    
    # Test valid retrieval
    response = client.get("/api/v1/dashboards/reports/treasury_liquidity_report.html", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "Corporate Treasury & Liquidity Sweep Analytics" in response.text

def test_dashboard_reports_include_storage_report_builder_outputs():
    """Dashboards must list reports published under Infra/storage/reports/report_*/index.html."""
    reports = get_dashboard_reports()

    storage_reports = [r for r in reports if r.get("source") == "storage"]
    assert storage_reports
    assert all(r["filename"].startswith("report_") and r["filename"].endswith(".html") for r in storage_reports)


def test_api_get_storage_dashboard_report():
    """Virtual report_*.html dashboard entries should resolve to report_*/index.html."""
    reports = get_dashboard_reports()
    storage_report = next((r for r in reports if r.get("source") == "storage"), None)
    assert storage_report is not None

    client = TestClient(app)
    token = "AIP-TEST-DASHBOARD-STORAGE-REPORT"
    set_session(token, {
        'username': 'Treasury_Analyst',
        'role': 'Analyst',
        'clearance': 'Internal',
        'display_name': 'Treasury Analyst'
    })

    response = client.get(
        f"/api/v1/dashboards/reports/{storage_report['filename']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "<html" in response.text.lower()
