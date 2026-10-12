def test_create_sprint(client, admin_headers):
    """
    Test Sprint Creation:
    Create 'Sprint 2 - Workflow & Collaboration'
    """
    payload = {
        "project_id": 1,
        "sprint_name": "Sprint 2 - Workflow & Collaboration",
        "goal": "Build state machine and sprint board",
        "status": "ACTIVE"
    }
    res = client.post("/api/v1/sprints/", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["sprint_name"] == "Sprint 2 - Workflow & Collaboration"
    assert data["status"] == "ACTIVE"

def test_add_issue_to_sprint(client, admin_headers, tester_headers):
    """
    Test 4 (Sprint Assignment Checklist):
    Create a new Sprint, move a backlog bug into it, verify it belongs to the sprint.
    """
    # 1. Create a bug without sprint (in backlog)
    bug_res = client.post("/api/v1/issues/", json={
        "project_id": 1,
        "category_id": 3,
        "title": "Unassigned backlog bug",
        "description": "Waiting for sprint assignment",
        "severity": "MINOR"
    }, headers=tester_headers)
    bug_id = bug_res.json()["id"]

    # 2. Move to Sprint 1
    assign_res = client.post(f"/api/v1/sprints/1/add-issue/{bug_id}", headers=admin_headers)
    assert assign_res.status_code == 200
    assert assign_res.json()["sprint_id"] == 1

    # 3. Verify in issue details
    get_bug = client.get(f"/api/v1/issues/{bug_id}", headers=admin_headers)
    assert get_bug.json()["sprint_id"] == 1

def test_sprint_velocity_calculation(client, admin_headers, tester_headers):
    """
    Velocity Tracker:
    When sprint is marked COMPLETED, verify velocity reflects resolved bugs count.
    """
    # Create Sprint 3
    sp_res = client.post("/api/v1/sprints/", json={
        "project_id": 1,
        "sprint_name": "Sprint 3 - Velocity Test",
        "status": "ACTIVE"
    }, headers=admin_headers)
    sprint_id = sp_res.json()["sprint_id"]

    # Create and resolve a bug in Sprint 3
    b_res = client.post("/api/v1/issues/", json={
        "project_id": 1,
        "category_id": 3,
        "title": "Bug for sprint 3",
        "description": "Will be resolved",
        "severity": "MINOR",
        "sprint_id": sprint_id
    }, headers=tester_headers)
    b_id = b_res.json()["id"]

    # Fast transition to RESOLVED via admin
    client.patch(f"/api/v1/issues/{b_id}/status", json={"status": "TRIAGED"}, headers=admin_headers)
    client.patch(f"/api/v1/issues/{b_id}/status", json={"status": "IN_PROGRESS"}, headers=admin_headers)
    client.patch(f"/api/v1/issues/{b_id}/status", json={"status": "CODE_REVIEW"}, headers=admin_headers)
    client.patch(f"/api/v1/issues/{b_id}/status", json={"status": "QA_VERIFICATION"}, headers=admin_headers)
    client.patch(f"/api/v1/issues/{b_id}/status", json={"status": "RESOLVED"}, headers=admin_headers)

    # Complete Sprint 3
    comp_res = client.patch(f"/api/v1/sprints/{sprint_id}/status?new_status=COMPLETED", headers=admin_headers)
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"
    assert comp_res.json()["velocity"] >= 1.0

def test_chat_comments_persistence(client, dev_headers):
    """
    Test 3 (Chat & Comments Checklist):
    Open a bug, post a comment, verify the comment persists and is retrievable.
    """
    issue_id = 1
    comment_text = "I reproduced this bug on Chrome v120 with 50 concurrent sessions."

    post_res = client.post(
        f"/api/v1/collaboration/issues/{issue_id}/comments",
        json={"content": comment_text},
        headers=dev_headers
    )
    assert post_res.status_code == 201
    assert post_res.json()["content"] == comment_text

    # Fetch comments
    get_res = client.get(
        f"/api/v1/collaboration/issues/{issue_id}/comments",
        headers=dev_headers
    )
    assert get_res.status_code == 200
    comments = get_res.json()
    assert any(c["content"] == comment_text for c in comments)
