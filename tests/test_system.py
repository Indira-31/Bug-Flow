import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_system_backup_and_restore(admin_auth_headers):
    # 1. Backup
    backup_resp = client.post("/api/v1/system/backup", headers=admin_auth_headers)
    assert backup_resp.status_code == 200
    b_data = backup_resp.json()
    assert b_data["status"] == "SUCCESS"
    assert b_data["backup_file"] is not None
    assert "counts" in b_data or "records_count" in b_data

    # 2. Restore verification
    restore_resp = client.post("/api/v1/system/restore", headers=admin_auth_headers)
    assert restore_resp.status_code == 200
    r_data = restore_resp.json()
    assert r_data["status"] == "SUCCESS"
    assert "validated" in r_data["message"].lower()


def test_retention_policy_evaluation(admin_auth_headers):
    resp = client.get(
        "/api/v1/system/retention-policy?retention_days=30",
        headers=admin_auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACTIVE"
    assert data["retention_period_days"] == 30
    assert "archived_or_evaluated_records" in data


def test_page10_schema_registries(admin_auth_headers):
    # Test user portals
    portals_resp = client.get("/api/v1/system/portals", headers=admin_auth_headers)
    assert portals_resp.status_code == 200
    portals = portals_resp.json()
    assert len(portals) >= 4
    portal_names = [p["portal_type"] for p in portals]
    assert "Web Dashboard" in portal_names
    assert "CI/CD Console" in portal_names

    # Test historical fixes
    fixes_resp = client.get("/api/v1/system/historical-fixes", headers=admin_auth_headers)
    assert fixes_resp.status_code == 200
    fixes = fixes_resp.json()
    assert len(fixes) >= 1

    # Test triage insights
    insights_resp = client.get("/api/v1/system/triage-insights", headers=admin_auth_headers)
    assert insights_resp.status_code == 200
    insights = insights_resp.json()
    assert len(insights) >= 1
