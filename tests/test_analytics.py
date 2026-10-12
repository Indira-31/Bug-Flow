def test_git_commit_webhook_auto_advancement(client, admin_headers):
    """
    Test 1 (Git Webhook Checklist):
    Send POST to /api/v1/webhooks/git with message 'Merge PR #45: fixes #1 connection crash'
    Verify Bug #1 automatically transitions to QA_VERIFICATION
    """
    res = client.post("/api/v1/webhooks/git", json={
        "commit_message": "Merge PR #45: fixes #1 connection crash",
        "commit_sha": "a7f8c92"
    })
    assert res.status_code == 200
    data = res.json()
    assert 1 in data["matched_issues"]

    # Verify Issue #1 status is now QA_VERIFICATION
    issue_res = client.get("/api/v1/issues/1", headers=admin_headers)
    assert issue_res.status_code == 200
    assert issue_res.json()["status"] == "QA_VERIFICATION"

def test_software_quality_metrics(client, dev_headers):
    """
    Test 2 (Metrics Math Checklist):
    Check /api/v1/analytics/quality-metrics
    Verify fix_rate_percentage and mean_time_to_resolution_hours calculate accurately
    """
    res = client.get("/api/v1/analytics/quality-metrics", headers=dev_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_bugs" in data
    assert "fix_rate_percentage" in data
    assert "mean_time_to_resolution_hours" in data
    assert "defect_leakage_rate_percentage" in data
    assert "backlog_health_score" in data
    assert 0.0 <= data["backlog_health_score"] <= 100.0

def test_plotly_chart_configs(client, dev_headers):
    """
    Test 3 (Plotly Charts Checklist):
    Verify /api/v1/analytics/plotly-charts returns valid Plotly data & layout structures
    """
    res = client.get("/api/v1/analytics/plotly-charts", headers=dev_headers)
    assert res.status_code == 200
    charts = res.json()
    assert "defect_trend" in charts
    assert "severity_donut" in charts
    assert "workflow_pipeline" in charts
    assert "data" in charts["defect_trend"]
    assert "layout" in charts["defect_trend"]

def test_pdf_quality_report_export(client):
    """
    Test 4 (PDF Download Checklist):
    Verify /api/v1/export/pdf returns a valid PDF document (%PDF)
    """
    res = client.get("/api/v1/export/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")

def test_csv_defect_registry_export(client):
    """
    Test 5 (CSV Download Checklist):
    Verify /api/v1/export/csv returns valid CSV text with bug columns
    """
    res = client.get("/api/v1/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    content = res.text
    assert "Bug ID" in content
    assert "Severity" in content
    assert "Priority" in content

def test_developer_workload_matrix(client, dev_headers):
    res = client.get("/api/v1/analytics/developer-workload", headers=dev_headers)
    assert res.status_code == 200
    devs = res.json()
    assert len(devs) >= 1
    assert "full_name" in devs[0]
    assert "active_tasks" in devs[0]
    assert "completed_fixes" in devs[0]

def test_system_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] in ["sqlite", "postgresql"]
    assert "pool_size" in data
