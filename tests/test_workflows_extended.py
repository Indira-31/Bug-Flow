import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_issue_types_and_tags_support(admin_auth_headers):
    # 1. Create Feature Request with tags
    payload = {
        "project_id": 1,
        "category_id": 3,
        "title": "Add multi-tenant organization support",
        "description": "Enterprise customers require isolated data tenants.",
        "issue_type": "FEATURE_REQUEST",
        "severity": "MAJOR",
        "tags": "multi-tenant, enterprise, security",
        "code_references": "rfc/002-tenants.md",
        "estimated_effort": 8.0
    }
    response = client.post("/api/v1/issues/", json=payload, headers=admin_auth_headers)
    assert response.status_code == 201
    created = response.json()
    assert created["issue_type"] == "FEATURE_REQUEST"
    assert "multi-tenant" in created["tags"]
    assert created["code_references"] == "rfc/002-tenants.md"

    # 2. Filter by issue_type
    filter_resp = client.get(
        "/api/v1/issues/?issue_type=FEATURE_REQUEST",
        headers=admin_auth_headers
    )
    assert filter_resp.status_code == 200
    items = filter_resp.json()
    assert any(i["id"] == created["id"] for i in items)


def test_issue_merging(admin_auth_headers, developer_auth_headers):
    # Create original issue
    p1 = {
        "project_id": 1,
        "category_id": 1,
        "title": "Primary Issue: Session hijacking via cookie flaw",
        "description": "Session cookie is missing Secure flag.",
        "severity": "CRITICAL"
    }
    r1 = client.post("/api/v1/issues/", json=p1, headers=admin_auth_headers)
    assert r1.status_code == 201
    primary_id = r1.json()["id"]

    # Create duplicate issue
    p2 = {
        "project_id": 1,
        "category_id": 1,
        "title": "Duplicate: Cookies missing secure attribute in production",
        "description": "Cookie flags need SameSite and Secure.",
        "severity": "CRITICAL"
    }
    r2 = client.post("/api/v1/issues/", json=p2, headers=admin_auth_headers)
    assert r2.status_code == 201
    duplicate_id = r2.json()["id"]

    # Add a comment to the duplicate issue
    client.post(
        f"/api/v1/collaboration/issues/{duplicate_id}/comments",
        json={"content": "Confirmed on staging cluster."},
        headers=developer_auth_headers
    )

    # Merge duplicate into primary
    merge_payload = {
        "duplicate_issue_id": duplicate_id,
        "merge_reason": "Identified as exact duplicate of security flaw"
    }
    merge_resp = client.post(
        f"/api/v1/issues/{primary_id}/merge",
        json=merge_payload,
        headers=admin_auth_headers
    )
    assert merge_resp.status_code == 200

    # Verify duplicate is now CLOSED and marked merged
    dup_check = client.get(f"/api/v1/issues/{duplicate_id}", headers=admin_auth_headers)
    assert dup_check.status_code == 200
    dup_data = dup_check.json()
    assert dup_data["status"] == "CLOSED"
    assert dup_data["merged_into_id"] == primary_id


def test_issue_escalation_workflow(admin_auth_headers, tester_auth_headers):
    # Create issue
    payload = {
        "project_id": 1,
        "category_id": 5,
        "title": "Intermittent UI spinner freezing",
        "description": "Spinner does not dismiss after upload completes.",
        "severity": "MINOR"
    }
    res = client.post("/api/v1/issues/", json=payload, headers=admin_auth_headers)
    assert res.status_code == 201
    issue_id = res.json()["id"]

    # Escalate
    esc_payload = {
        "reason": "Affects enterprise demo tomorrow morning",
        "target_priority": "URGENT"
    }
    esc_resp = client.post(
        f"/api/v1/issues/{issue_id}/escalate",
        json=esc_payload,
        headers=tester_auth_headers
    )
    assert esc_resp.status_code == 200
    esc_data = esc_resp.json()
    assert esc_data["is_escalated"] is True
    assert esc_data["priority"] == "URGENT"
    assert "enterprise demo" in esc_data["escalation_reason"]


def test_issue_approval_workflow(admin_auth_headers, developer_auth_headers):
    # Create issue
    payload = {
        "project_id": 1,
        "category_id": 4,
        "title": "API rate limiter threshold calibration",
        "description": "Rate limiter needs burst capacity tuning.",
        "severity": "MAJOR"
    }
    res = client.post("/api/v1/issues/", json=payload, headers=admin_auth_headers)
    assert res.status_code == 201
    issue_id = res.json()["id"]

    # Advance to TRIAGED -> IN_PROGRESS -> CODE_REVIEW using admin permissions
    r_triage = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "TRIAGED"}, headers=admin_auth_headers)
    assert r_triage.status_code == 200
    r_inprog = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "IN_PROGRESS"}, headers=admin_auth_headers)
    assert r_inprog.status_code == 200
    r_review = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "CODE_REVIEW"}, headers=admin_auth_headers)
    assert r_review.status_code == 200

    # Approve CODE_REVIEW -> moves to QA_VERIFICATION
    app_resp = client.post(
        f"/api/v1/issues/{issue_id}/approve",
        json={"approval_notes": "Code changes inspected and approved by lead"},
        headers=developer_auth_headers
    )
    assert app_resp.status_code == 200
    app_data = app_resp.json()
    assert app_data["is_approved"] is True
    assert app_data["status"] == "QA_VERIFICATION"


def test_release_milestones_and_readiness(admin_auth_headers, developer_auth_headers):
    # 1. Create Release
    rel_payload = {
        "project_id": 1,
        "version_name": "v2.0.0-Milestone-Beta",
        "status": "IN_PROGRESS",
        "release_notes": "Next major platform upgrade"
    }
    r_resp = client.post("/api/v1/releases/", json=rel_payload, headers=admin_auth_headers)
    assert r_resp.status_code == 201
    release_id = r_resp.json()["release_id"]

    # 2. Assign issue to release
    issue_payload = {
        "project_id": 1,
        "category_id": 2,
        "title": "Database connection pool tuning for v2.0",
        "description": "Configuring pool sizing for 10k RPS",
        "severity": "CRITICAL"
    }
    i_resp = client.post("/api/v1/issues/", json=issue_payload, headers=admin_auth_headers)
    issue_id = i_resp.json()["id"]

    assign_resp = client.post(
        f"/api/v1/releases/{release_id}/assign-issue/{issue_id}",
        headers=admin_auth_headers
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["release_id"] == release_id

    # 3. Check release readiness
    readiness_resp = client.get(
        f"/api/v1/releases/{release_id}/readiness",
        headers=admin_auth_headers
    )
    assert readiness_resp.status_code == 200
    readiness = readiness_resp.json()
    assert readiness["total_issues"] >= 1
    assert readiness["open_blockers_count"] >= 1
    assert readiness["readiness_status"] in ["AT_RISK", "BLOCKED"]


def test_cicd_pipeline_webhook_trigger(admin_auth_headers):
    # Create issue
    payload = {
        "project_id": 1,
        "category_id": 3,
        "title": "Cache invalidation on profile update",
        "description": "Clear Redis cache on user name change.",
        "severity": "MINOR"
    }
    i_res = client.post("/api/v1/issues/", json=payload, headers=admin_auth_headers)
    issue_id = i_res.json()["id"]

    # Trigger CI/CD deploy webhook
    cicd_payload = {
        "pipeline_id": "GH-ACTION-9082",
        "issue_ids": [issue_id],
        "stage": "DEPLOY",
        "build_status": "SUCCESS",
        "details": "Deployed to production cluster"
    }
    response = client.post("/api/v1/webhooks/cicd", json=cicd_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert issue_id in data["affected_issues"]

    # Verify issue is now RESOLVED
    check_res = client.get(f"/api/v1/issues/{issue_id}", headers=admin_auth_headers)
    assert check_res.json()["status"] == "RESOLVED"
