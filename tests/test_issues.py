def test_priority_calculation_critical_security(client, tester_headers):
    """
    Test 1 (Priority Math Checklist):
    Submit CRITICAL severity under Security Vulnerability category (Urgency=3)
    Verify Priority Score = 4 * 3 = 12.0 and Priority = URGENT
    """
    payload = {
        "project_id": 1,
        "category_id": 1,  # Security Vulnerability (High Urgency = 3)
        "title": "Zero-day Remote Code Execution in Session Handler",
        "description": "Unsanitized payload deserialization allows arbitrary command execution.",
        "severity": "CRITICAL",  # 4 pts
        "dev_stage": "Production",
        "affected_modules": "Auth, Session"
    }
    res = client.post("/api/v1/issues/", json=payload, headers=tester_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["priority_score"] == 12.0
    assert data["priority"] == "URGENT"
    assert data["status"] == "REPORTED"

def test_priority_calculation_minor_ui(client, tester_headers):
    """
    Test Priority Math:
    Submit MINOR severity (2) under UI Glitch category (Urgency=1)
    Verify Priority Score = 2 * 1 = 2.0 and Priority = LOW
    """
    payload = {
        "project_id": 1,
        "category_id": 5,  # UI Glitch (Low Urgency = 1)
        "title": "Minor typo in footer copyright label",
        "description": "Year says 2023 instead of 2026",
        "severity": "MINOR",  # 2 pts
        "dev_stage": "Development",
        "affected_modules": "Footer"
    }
    res = client.post("/api/v1/issues/", json=payload, headers=tester_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["priority_score"] == 2.0
    assert data["priority"] == "LOW"

def test_smart_developer_matcher(client, triager_headers):
    """
    Test 2 (Smart Match Checklist):
    Submit bug with 'database connection timeout'
    Verify backend/database developer (John Doe) appears as top recommendation
    """
    payload = {
        "title": "PostgreSQL database connection timeout pool exhausted",
        "description": "Queries to postgresql hang indefinitely under concurrent connections",
        "severity": "CRITICAL",
        "category_id": 2,  # Database Error
        "affected_modules": "Database"
    }
    res = client.post("/api/v1/issues/triage-recommendation", json=payload, headers=triager_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["priority"] == "URGENT"
    assert data["priority_score"] == 12.0
    assert len(data["recommended_developers"]) > 0

    top_dev = data["recommended_developers"][0]
    assert "John Doe" in top_dev["full_name"]
    assert top_dev["match_percentage"] >= 60.0
    assert "specialist" in top_dev["rationale"].lower() or "active task" in top_dev["rationale"].lower()

def test_duplicate_detection(client, dev_headers):
    """
    Duplicate Detection:
    Title similar to 'Existing Database connection timeout' (Issue #1 in test DB)
    Should trigger similarity >= 55%
    """
    # 1. Very similar title
    dup_res = client.post("/api/v1/issues/check-duplicates", json={
        "project_id": 1,
        "title": "Database connection timeout error in postgres"
    }, headers=dev_headers)
    assert dup_res.status_code == 200
    dup_data = dup_res.json()
    assert dup_data["is_duplicate"] is True
    assert len(dup_data["matches"]) >= 1
    assert dup_data["matches"][0]["similarity_score"] >= 55.0

    # 2. Completely distinct title
    distinct_res = client.post("/api/v1/issues/check-duplicates", json={
        "project_id": 1,
        "title": "Completely unrelated frontend CSS animation jitter"
    }, headers=dev_headers)
    assert distinct_res.status_code == 200
    assert distinct_res.json()["is_duplicate"] is False

def test_lifecycle_state_machine_workflow(client, admin_headers, dev_headers, tester_headers):
    """
    Lifecycle State Transitions:
    REPORTED -> TRIAGED -> IN_PROGRESS -> CODE_REVIEW -> QA_VERIFICATION -> RESOLVED -> CLOSED
    """
    # 1. Create fresh issue
    create_res = client.post("/api/v1/issues/", json={
        "project_id": 1,
        "category_id": 3,
        "title": "Lifecycle test bug workflow defect",
        "description": "Testing full transition sequence",
        "severity": "MAJOR"
    }, headers=tester_headers)
    assert create_res.status_code == 201
    issue_id = create_res.json()["id"]

    # 2. REPORTED -> TRIAGED
    res_triaged = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "TRIAGED"}, headers=admin_headers)
    assert res_triaged.status_code == 200
    assert res_triaged.json()["status"] == "TRIAGED"

    # 3. TRIAGED -> IN_PROGRESS (Auto-assigns dev_headers user: John Doe)
    res_progress = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "IN_PROGRESS"}, headers=dev_headers)
    assert res_progress.status_code == 200
    assert res_progress.json()["status"] == "IN_PROGRESS"
    assert res_progress.json()["assignee_id"] is not None

    # 4. IN_PROGRESS -> CODE_REVIEW
    res_review = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "CODE_REVIEW"}, headers=dev_headers)
    assert res_review.status_code == 200
    assert res_review.json()["status"] == "CODE_REVIEW"

    # 5. CODE_REVIEW -> QA_VERIFICATION
    res_qa = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "QA_VERIFICATION"}, headers=admin_headers)
    assert res_qa.status_code == 200
    assert res_qa.json()["status"] == "QA_VERIFICATION"

    # 6. QA_VERIFICATION -> RESOLVED
    res_resolved = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "RESOLVED"}, headers=admin_headers)
    assert res_resolved.status_code == 200
    assert res_resolved.json()["status"] == "RESOLVED"
    assert res_resolved.json()["resolved_at"] is not None

    # 7. RESOLVED -> CLOSED
    res_closed = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "CLOSED"}, headers=admin_headers)
    assert res_closed.status_code == 200
    assert res_closed.json()["status"] == "CLOSED"

    # 8. Reopen ticket: CLOSED -> IN_PROGRESS
    res_reopen = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "IN_PROGRESS"}, headers=admin_headers)
    assert res_reopen.status_code == 200
    assert res_reopen.json()["status"] == "IN_PROGRESS"
    assert res_reopen.json()["resolved_at"] is None

def test_invalid_lifecycle_transition_disallowed(client, admin_headers, tester_headers):
    """
    Invalid Transition:
    Cannot jump directly from REPORTED to RESOLVED
    """
    create_res = client.post("/api/v1/issues/", json={
        "project_id": 1,
        "category_id": 3,
        "title": "Bug for invalid transition test",
        "description": "Direct jump must fail",
        "severity": "MINOR"
    }, headers=tester_headers)
    issue_id = create_res.json()["id"]

    bad_res = client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "RESOLVED"}, headers=admin_headers)
    assert bad_res.status_code == 400
    assert "Cannot transition directly from REPORTED to RESOLVED" in bad_res.json()["detail"]

def test_audit_logs_recorded(client, admin_headers, tester_headers):
    """
    Test 5 (Audit Log Checklist):
    Verify that changing issue status records audit log entry
    """
    create_res = client.post("/api/v1/issues/", json={
        "project_id": 1,
        "category_id": 3,
        "title": "Audit verification issue",
        "description": "Checking audit trail",
        "severity": "MINOR"
    }, headers=tester_headers)
    issue_id = create_res.json()["id"]

    # Transition to TRIAGED
    client.patch(f"/api/v1/issues/{issue_id}/status", json={"status": "TRIAGED"}, headers=admin_headers)

    # Fetch issue details
    detail_res = client.get(f"/api/v1/issues/{issue_id}", headers=admin_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["audit_logs"]) >= 2
    status_log = [l for l in detail["audit_logs"] if l["action"] == "STATUS_CHANGE"]
    assert len(status_log) > 0
    assert status_log[0]["old_value"] == "REPORTED"
    assert status_log[0]["new_value"] == "TRIAGED"
