import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_ai_core_analysis_pipeline(admin_auth_headers):
    payload = {
        "title": "PostgreSQL database connection leak causing fatal crash",
        "description": "Peak queries leave idle connections open until database runs out of connections and crashes.",
        "category_id": 2,  # Database Error
        "severity": "CRITICAL",
        "code_diff": "diff --git a/database.py b/database.py\n+ pool_pre_ping=True",
        "project_context": "FastAPI with SQLAlchemy backend service",
        "affected_modules": "Database, ConnectionPool"
    }

    response = client.post(
        "/api/v1/issues/ai-core-analysis",
        json=payload,
        headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()

    # Verify Page 10 outputs
    assert data["ai_ethical_bias_passed"] is True
    assert "PASSED" in data["ethical_bias_report"]
    assert data["suggested_severity"] == "CRITICAL"
    assert data["priority"] in ["URGENT", "HIGH"]
    assert len(data["personalized_resolution_path"]) >= 4
    assert len(data["matched_historical_patterns"]) >= 1
    assert "rollback" in data["automated_cicd_rollback_path"].lower()
    assert "cycle_insights" in data
    assert len(data["developer_assignments"]) >= 1
