# BugFlow – Enterprise Software Issue Tracking & Resolution Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-red?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Pytest](https://img.shields.io/badge/Pytest-100%25_Passing-brightgreen?logo=pytest&logoColor=white)](https://pytest.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker&logoColor=white)](https://docker.com)

BugFlow is a full-stack, enterprise-grade software defect management and issue resolution platform built with Python 3.10+, FastAPI, SQLAlchemy 2.0 connection pooling, PostgreSQL persistence, and responsive Tailwind CSS / Plotly.js frontend dashboards.

---

## 🏛️ System Architecture

```
                                +---------------------------------------------+
                                |      Browser / Web UI / Mobile App          |
                                | (Tailwind CSS, Plotly.js, Responsive SPA)   |
                                +----------------------+----------------------+
                                                       | REST HTTP / Bearer JWT
                                                       v
+---------------------------------------------------------------------------------------------------------+
|                                      FastAPI Async ASGI Application                                      |
|                                                                                                         |
|  [Security & Auth Middleware] (bcrypt, JWT HMAC-SHA256, 5-Role RBAC: Admin, Dev, Tester, Triager, etc.)|
|                                                                                                         |
|  +------------------------+  +--------------------------+  +------------------------------------------+ |
|  |     Issues Router      |  |   Collaboration Router   |  |            Sprints Router                | |
|  | - Submission & Ingest  |  | - Threaded Comments      |  | - 2-Week Agile Sprints                   | |
|  | - State Transitions    |  | - Attachment Files       |  | - Backlog Ingest & Assignment            | |
|  | - Duplicate Detection  |  | - Immutable Audit Trail  |  | - Velocity Tracker                       | |
|  +------------------------+  +--------------------------+  +------------------------------------------+ |
|                                                                                                         |
|  +------------------------+  +--------------------------+  +------------------------------------------+ |
|  |    Webhooks Router     |  |     Analytics Router     |  |              Export Router               | |
|  | - CI/CD Git Commits    |  | - Quality Scorecard      |  | - PDF Executive Reports                  | |
|  | - Auto QA Transitions  |  | - 14-Day Defect Trends   |  | - CSV Spreadsheets                       | |
|  +------------------------+  +--------------------------+  +------------------------------------------+ |
+------------------------------------------------------+--------------------------------------------------+
                                                       | Connection Pool (pool_size=20, max_overflow=10)
                                                       v
+---------------------------------------------------------------------------------------------------------+
|                                      PostgreSQL 15+ Relational DB                                       |
|  - Users | Projects | BugCategories | Issues | Sprints | Comments | Attachments | AuditLogs             |
|  - Composite Indexes: (project_id, status), (assignee_id, status), (created_at)                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 🚀 Key Modules & Milestones

### 1. Milestone 1: Issue Reporting & Foundation Management
- **5-Role Granular RBAC**: `ADMIN`, `DEVELOPER`, `TESTER`, `TRIAGER`, `STAKEHOLDER`.
- **Stateless JWT Auth**: HMAC-SHA256 encryption with bcrypt salt hashing.
- **Smart Priority Score**: 
  $$\text{Priority Score} = \text{Severity Weight} \times \text{Category Urgency Weight}$$
- **Duplicate Detection**: Real-time Jaccard token overlap & Levenshtein distance check flagging duplicates with $\ge 55\%$ similarity.
- **Validated State Machine**: `REPORTED ➔ TRIAGED ➔ IN_PROGRESS ➔ CODE_REVIEW ➔ QA_VERIFICATION ➔ RESOLVED ➔ CLOSED`.
- **Immutable Audit Trail**: Logs every field change, user timestamp, and status transition.

### 2. Milestone 2: Workflow & Collaboration
- **Smart Developer Matcher**: NLP keyword analysis + developer skill profiles + active task workload penalty.
- **Discussion Threads & Comments**: Direct defect conversation stream.
- **Screenshot & Log Uploader**: Supports `.png`, `.jpg`, `.log`, `.txt`, `.pdf`.
- **2-Week Agile Sprint Board**: Drag/move backlog bugs into active sprints with automatic velocity calculation upon completion.

### 3. Milestone 3: CI/CD Webhooks & Analytics
- **Automated Git Webhook**: Ingests commit messages (e.g. `fixes #2`), automatically transitioning issues to `QA_VERIFICATION`.
- **Software Quality Scorecard**:
  - **Fix Rate %**: $\frac{\text{Resolved} + \text{Closed}}{\text{Total}} \times 100$
  - **MTTR**: Average hours from creation to resolution.
  - **Defect Leakage Rate %**: Production bugs vs. total bugs.
  - **Backlog Health Score (0 - 100)**: Quality score with critical bug weighting.
- **Interactive Plotly.js Visualizations**: 14-day defect trends line chart, severity donut chart, and workflow pipeline bar chart.
- **One-Click Export**: Formatted PDF Quality Reports and Excel-ready CSV defect registers.

### 4. Milestone 4: Team Productivity & System Scale
- **Developer Workload Matrix**: Resource balance indicator tracking active tasks, completed fixes, and average turnaround time.
- **Database Speed Optimization**: Composite indexes on `(project_id, status)`, `(assignee_id, status)`, and `(created_at)`.
- **Connection Pooling**: Reusable connection pool (`pool_size=20, max_overflow=10, pool_pre_ping=True`).
- **Comprehensive Pytest Suite**: 25 automated unit and integration tests passing with 100% green checkmarks.

---

## 📦 Quick Start & Installation

### Option A: Local Python Execution

1. **Activate your environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**:
   ```bash
   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. **Access the application**:
   - Web Dashboard: [http://localhost:8000/](http://localhost:8000/)
   - Swagger OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc Manual: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

### Option B: Multi-Container Docker Deployment

Run both the FastAPI app and PostgreSQL 15 container in one command:
```bash
docker compose up --build
```

---

## 🧪 Running Automated Tests

Run the complete Pytest test suite:
```bash
python -m pytest tests/ -v
```
All 25 test cases will run and pass with green checkmarks.

---

## 👥 Default Demo Credentials

| Role | Username | Password | Full Name | Primary Focus |
| :--- | :--- | :--- | :--- | :--- |
| **ADMIN** | `admin` | `adminpassword123` | Alex Rivera | Platform Administration |
| **DEVELOPER** | `john_dev` | `devpassword123` | John Doe | Backend, PostgreSQL, Python |
| **DEVELOPER** | `alice_dev` | `devpassword123` | Alice Smith | Frontend, React, CSS, UI |
| **TESTER** | `bruce_tester` | `testerpassword123`| Bruce Wayne | QA Verification & Defect Reporting |
| **TRIAGER** | `tina_triager` | `triagerpassword123`| Tina Turner | Bug Triage & Sprint Allocation |
| **STAKEHOLDER**| `sam_stakeholder`| `stakeholderpassword123`| Sam Altman | Quality Scorecards & Reports |
