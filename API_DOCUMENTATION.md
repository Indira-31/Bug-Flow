# BugFlow REST API Reference Manual (v1.0)

Interactive OpenAPI Swagger UI is available live at `http://localhost:8000/docs`.
Interactive ReDoc documentation is available at `http://localhost:8000/redoc`.

Base URL: `http://localhost:8000/api/v1`

---

## 1. Authentication Endpoints

### 1.1 Register User
- **Method**: `POST`
- **Endpoint**: `/api/v1/auth/register`
- **Auth**: None
- **Request Body**:
  ```json
  {
    "username": "sarah_dev",
    "email": "sarah@company.io",
    "password": "StrongPassword123!",
    "full_name": "Sarah Connor",
    "role": "DEVELOPER",
    "team": "Cloud Infrastructure",
    "core_skills": "Kubernetes, Go, Python, Docker",
    "proficiency": "Senior"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": 7,
    "username": "sarah_dev",
    "email": "sarah@company.io",
    "full_name": "Sarah Connor",
    "role": "DEVELOPER",
    "team": "Cloud Infrastructure",
    "core_skills": "Kubernetes, Go, Python, Docker",
    "proficiency": "Senior",
    "is_active": true,
    "created_at": "2026-09-21T08:30:00Z"
  }
  ```

### 1.2 Login & Receive Token
- **Method**: `POST`
- **Endpoint**: `/api/v1/auth/login`
- **Auth**: None
- **Request Body**:
  ```json
  {
    "username": "admin",
    "password": "adminpassword123"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@bugflow.io",
      "full_name": "Alex Rivera (Admin)",
      "role": "ADMIN"
    }
  }
  ```

### 1.3 Current User Profile
- **Method**: `GET`
- **Endpoint**: `/api/v1/auth/me`
- **Auth**: Bearer JWT

---

## 2. Issue Management Endpoints

### 2.1 Submit New Issue
- **Method**: `POST`
- **Endpoint**: `/api/v1/issues/`
- **Auth**: Bearer JWT (`ADMIN`, `TESTER`, `DEVELOPER`, `TRIAGER`)
- **Request Body**:
  ```json
  {
    "project_id": 1,
    "category_id": 1,
    "title": "SQL Injection vulnerability on customer search API",
    "description": "Unescaped raw SQL parameter passed to repository query.",
    "reproduction_steps": "1. Send ' OR 1=1 -- to /api/search\n2. All records returned",
    "severity": "CRITICAL",
    "affected_modules": "Search, SQLRepository",
    "environment_details": "Production API Gateway",
    "dev_stage": "Production",
    "estimated_effort": 3.0
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": 7,
    "project_id": 1,
    "title": "SQL Injection vulnerability on customer search API",
    "severity": "CRITICAL",
    "priority": "URGENT",
    "priority_score": 12.0,
    "status": "REPORTED",
    "created_at": "2026-09-21T08:31:00Z"
  }
  ```

### 2.2 List Issues
- **Method**: `GET`
- **Endpoint**: `/api/v1/issues/`
- **Query Params**:
  - `project_id` (int, optional)
  - `status` (string, optional)
  - `severity` (string, optional)
  - `assignee_id` (int, optional)
  - `sprint_id` (int, optional)
  - `search` (string, optional)
  - `skip` (int, default: 0)
  - `limit` (int, default: 50, max: 200)

### 2.3 Transition Lifecycle State
- **Method**: `PATCH`
- **Endpoint**: `/api/v1/issues/{id}/status`
- **Auth**: Bearer JWT (`DEVELOPER`, `TESTER`, `ADMIN`)
- **Request Body**:
  ```json
  {
    "status": "IN_PROGRESS"
  }
  ```

### 2.4 Assign Issue
- **Method**: `PATCH`
- **Endpoint**: `/api/v1/issues/{id}/assign`
- **Auth**: Bearer JWT (`ADMIN`, `TRIAGER`, `DEVELOPER`)
- **Request Body**:
  ```json
  {
    "assignee_id": 2
  }
  ```

### 2.5 Real-Time Duplicate Check
- **Method**: `POST`
- **Endpoint**: `/api/v1/issues/check-duplicates`
- **Request Body**:
  ```json
  {
    "project_id": 1,
    "title": "Database connection pool timeout error"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "is_duplicate": true,
    "threshold": 0.55,
    "matches": [
      {
        "id": 1,
        "title": "Database connection pool timeout under load",
        "similarity_score": 85.0,
        "status": "RESOLVED",
        "severity": "CRITICAL"
      }
    ]
  }
  ```

### 2.6 Triage Recommendation & Smart Developer Match
- **Method**: `POST`
- **Endpoint**: `/api/v1/issues/triage-recommendation`
- **Request Body**:
  ```json
  {
    "title": "Database connection pool timeout",
    "description": "PostgreSQL driver drops connection pool",
    "severity": "CRITICAL",
    "category_id": 2,
    "affected_modules": "Database"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "priority_score": 12.0,
    "priority": "URGENT",
    "severity_weight": 4,
    "urgency_weight": 3,
    "recommended_developers": [
      {
        "user_id": 2,
        "full_name": "John Doe (Backend)",
        "username": "john_dev",
        "team": "Backend Engineering",
        "core_skills": "Python, PostgreSQL, Database, SQL, FastAPI",
        "active_tasks": 1,
        "match_percentage": 92.0,
        "rationale": "Database specialist, 1 active task"
      }
    ]
  }
  ```

---

## 3. Collaboration Endpoints

### 3.1 Post Comment
- **Method**: `POST`
- **Endpoint**: `/api/v1/collaboration/issues/{id}/comments`
- **Request Body**: `{"content": "I reproduced this bug on Chrome v122."}`

### 3.2 Fetch Comments
- **Method**: `GET`
- **Endpoint**: `/api/v1/collaboration/issues/{id}/comments`

### 3.3 Upload Attachment
- **Method**: `POST`
- **Endpoint**: `/api/v1/collaboration/issues/{id}/attachments`
- **Content-Type**: `multipart/form-data`
- **File Types**: `.png`, `.jpg`, `.jpeg`, `.log`, `.txt`, `.pdf`

---

## 4. Agile Sprints Endpoints

### 4.1 Create Sprint
- **Method**: `POST`
- **Endpoint**: `/api/v1/sprints/`
- **Request Body**:
  ```json
  {
    "project_id": 1,
    "sprint_name": "Sprint 3 - Performance & Resilience",
    "goal": "Optimize connection pool latency and add caching",
    "status": "ACTIVE"
  }
  ```

### 4.2 Move Bug to Sprint
- **Method**: `POST`
- **Endpoint**: `/api/v1/sprints/{sprint_id}/add-issue/{issue_id}`

### 4.3 Complete Sprint & Calculate Velocity
- **Method**: `PATCH`
- **Endpoint**: `/api/v1/sprints/{sprint_id}/status?new_status=COMPLETED`

---

## 5. CI/CD Git Webhook Endpoints

### 5.1 Ingest Git Push Commit
- **Method**: `POST`
- **Endpoint**: `/api/v1/webhooks/git`
- **Auth**: None / CI Webhook Secret
- **Request Body**:
  ```json
  {
    "commit_message": "Merge PR #45: fixes #2 login password crash",
    "commit_sha": "a7f8c92",
    "branch": "main",
    "author": "john_dev"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "status": "success",
    "matched_issues": [2],
    "message": "Processed commit a7f8c92. Auto-advanced 1 issue(s) to QA_VERIFICATION."
  }
  ```

---

## 6. Analytics & Export Endpoints

### 6.1 Quality Metrics Scorecard
- **Method**: `GET`
- **Endpoint**: `/api/v1/analytics/quality-metrics`
- **Response** (`200 OK`):
  ```json
  {
    "total_bugs": 6,
    "resolved_bugs": 1,
    "closed_bugs": 0,
    "open_bugs": 5,
    "fix_rate_percentage": 16.7,
    "mean_time_to_resolution_hours": 48.0,
    "defect_leakage_rate_percentage": 16.7,
    "backlog_health_score": 51.0
  }
  ```

### 6.2 Plotly Charts Configurations
- **Method**: `GET`
- **Endpoint**: `/api/v1/analytics/plotly-charts`
- **Returns**: Formatted Plotly `data` and `layout` configs for:
  1. `defect_trend` (14-day line graph)
  2. `severity_donut` (donut chart)
  3. `workflow_pipeline` (bar chart)

### 6.3 Developer Workload Matrix
- **Method**: `GET`
- **Endpoint**: `/api/v1/analytics/developer-workload`

### 6.4 Export PDF Report
- **Method**: `GET`
- **Endpoint**: `/api/v1/export/pdf`
- **Returns**: `application/pdf` binary download stream

### 6.5 Export CSV Registry
- **Method**: `GET`
- **Endpoint**: `/api/v1/export/csv`
- **Returns**: `text/csv` spreadsheet download

---

## 7. Advanced Issue Workflows

### 7.1 Merge Duplicate Issue (Module 1)
- **Method**: `POST`
- **Endpoint**: `/api/v1/issues/{id}/merge`
- **Auth**: Bearer JWT (`ADMIN`, `TRIAGER`, `DEVELOPER`)
- **Request Body**:
  ```json
  {
    "duplicate_issue_id": 3,
    "merge_reason": "Duplicate report identified during triage"
  }
  ```
- **Response** (`200 OK`): Primary issue with comments copied and duplicate closed with audit record.

### 7.2 Escalate Issue (Module 3)
- **Method**: `POST`
- **Endpoint**: `/api/v1/issues/{id}/escalate`
- **Auth**: Bearer JWT (`ADMIN`, `TESTER`, `TRIAGER`)
- **Request Body**:
  ```json
  {
    "reason": "Critical blocking bug discovered before executive release demo",
    "target_priority": "URGENT"
  }
  ```

### 7.3 Approve Stage Transition (Module 3)
- **Method**: `POST`
- **Endpoint**: `/api/v1/issues/{id}/approve`
- **Auth**: Bearer JWT (`ADMIN`, `DEVELOPER`, `TESTER`)
- **Request Body**:
  ```json
  {
    "approval_notes": "Code inspection and regression suite verified by lead"
  }
  ```

---

## 8. BugFlow AI Core Engine (Page 10 Architecture Pipeline)

### 8.1 Execute AI Core Analysis
- **Method**: `POST`
- **Endpoint**: `/api/v1/issues/ai-core-analysis`
- **Auth**: Bearer JWT
- **Request Body**:
  ```json
  {
    "title": "PostgreSQL database connection leak causing fatal crash",
    "description": "Peak queries leave idle connections open until database runs out of connections and crashes.",
    "category_id": 2,
    "severity": "CRITICAL",
    "code_diff": "diff --git a/database.py b/database.py\n+ pool_pre_ping=True",
    "affected_modules": "Database, ConnectionPool"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "analyzed_title": "PostgreSQL database connection leak causing fatal crash",
    "analyzed_severity": "CRITICAL",
    "ai_ethical_bias_passed": true,
    "ethical_bias_report": "PASSED: Issue content is verified purely technical with zero demographic bias.",
    "categorization": "Database Error",
    "suggested_severity": "CRITICAL",
    "priority_score": 12.0,
    "priority": "URGENT",
    "matched_historical_patterns": [
      {
        "fix_id": 1,
        "past_fixes": "Resolved PostgreSQL idle connection drop in DB pool",
        "resolution_time": "1.5 days",
        "suggested_approach": "Increased pool_pre_ping=True and pool_recycle=1800 in database.py"
      }
    ],
    "personalized_resolution_path": [
      {
        "step": 1,
        "phase": "Reproduction & Root Cause Isolation",
        "action": "Replicate issue locally using specified environment. Check logs for 'Database Error'.",
        "suggested_tests": ["Unit test for edge case regression"]
      },
      {
        "step": 2,
        "phase": "Fix Development & Code Review",
        "action": "Implement patch on feature branch, reference issue in commit message (fixes #ID).",
        "suggested_tests": ["Integration API test verification", "PostgreSQL connection pool stress test (100 conns)"]
      },
      {
        "step": 3,
        "phase": "QA Validation & Regression Testing",
        "action": "Automated CI/CD verifies test suite. Peer review by assigned senior engineer.",
        "suggested_tests": ["DB transaction rollback test"]
      },
      {
        "step": 4,
        "phase": "Release Deployment & Patching",
        "action": "Deploy via automated pipeline with active rollback trigger on health check failure.",
        "suggested_tests": ["End-to-end smoke test on staging"]
      }
    ],
    "developer_assignments": [
      {
        "user_id": 2,
        "full_name": "John Doe (Backend)",
        "username": "john_dev",
        "team": "Backend Engineering",
        "core_skills": "Python, PostgreSQL, Database, SQL, FastAPI, Redis",
        "active_tasks": 2,
        "match_percentage": 94.0,
        "rationale": "Direct skill match: Database, PostgreSQL (Senior Mid/Senior tier)"
      }
    ],
    "automated_cicd_rollback_path": "Automated CI/CD Pipeline: If post-deployment error rate exceeds 0.5% within 15 minutes, execute automated rollback via Git tag reversal and container blue-green switch.",
    "cycle_insights": "Based on current team velocity and Database Error complexity, expected resolution time is 1.5 days. Recommended sprint allocation: active cycle."
  }
  ```

---

## 9. Release Milestones & Readiness Management (Module 4)

### 9.1 Create Release
- **Method**: `POST`
- **Endpoint**: `/api/v1/releases/`
- **Auth**: Bearer JWT (`ADMIN`, `TRIAGER`)

### 9.2 List Releases
- **Method**: `GET`
- **Endpoint**: `/api/v1/releases/`

### 9.3 Assign Issue to Release
- **Method**: `POST`
- **Endpoint**: `/api/v1/releases/{id}/assign-issue/{issue_id}`

### 9.4 Release Readiness Assessment
- **Method**: `GET`
- **Endpoint**: `/api/v1/releases/{id}/readiness`
- **Response** (`200 OK`):
  ```json
  {
    "release_id": 1,
    "version_name": "v1.0.0-GA",
    "status": "IN_PROGRESS",
    "readiness_status": "AT_RISK",
    "readiness_percentage": 25.0,
    "total_issues": 4,
    "resolved_issues": 1,
    "open_blockers_count": 2,
    "blocking_issues": [
      { "id": 2, "title": "Login password crash", "severity": "CRITICAL", "status": "IN_PROGRESS" }
    ]
  }
  ```

---

## 10. System Administration & Maintenance (Module 5 & Page 10)

### 10.1 Backup Database
- **Method**: `POST`
- **Endpoint**: `/api/v1/system/backup`
- **Auth**: Bearer JWT (`ADMIN`)

### 10.2 Verify Database Restore
- **Method**: `POST`
- **Endpoint**: `/api/v1/system/restore`
- **Auth**: Bearer JWT (`ADMIN`)

### 10.3 Historical Retention Policy Check
- **Method**: `GET`
- **Endpoint**: `/api/v1/system/retention-policy?retention_days=90`
- **Auth**: Bearer JWT (`ADMIN`)

### 10.4 Query BugFlow User Portals
- **Method**: `GET`
- **Endpoint**: `/api/v1/system/portals`
- **Auth**: Bearer JWT

---

## 11. CI/CD Pipeline Automation (Module 6)

### 11.1 CI/CD Pipeline Status Synchronization
- **Method**: `POST`
- **Endpoint**: `/api/v1/webhooks/cicd`
- **Request Body**:
  ```json
  {
    "pipeline_id": "GH-ACTION-9082",
    "issue_ids": [2],
    "stage": "DEPLOY",
    "build_status": "SUCCESS",
    "details": "Automated deployment to production cluster"
  }
  ```

