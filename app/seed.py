from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models import (
    User, Project, BugCategory, Sprint, Release, Issue, Comment, AuditLog,
    IndividualBugSaga, ReporterIssueTracking, IssueAssignment,
    HistoricalBugFix, UserTriageInsight, BugFlowUserPortal
)
from app.auth import get_password_hash
from app.services.priority_service import calculate_priority

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        user_count = db.query(User).count()
        if user_count == 0:
            print("Seeding BugFlow initial database...")

            # 1. Bug Categories
            categories = [
                BugCategory(category_name="Security Vulnerability", urgency="High Urgency"),
                BugCategory(category_name="Database Error", urgency="High Urgency"),
                BugCategory(category_name="Backend Logic", urgency="Medium Urgency"),
                BugCategory(category_name="API Gateway", urgency="Medium Urgency"),
                BugCategory(category_name="UI Glitch", urgency="Low Urgency"),
            ]
            db.add_all(categories)
            db.commit()

            # 2. Users (5 Roles)
            users = [
                User(
                    username="admin",
                    email="admin@bugflow.io",
                    hashed_password=get_password_hash("adminpassword123"),
                    full_name="Alex Rivera (Admin)",
                    role="ADMIN",
                    team="Platform Operations",
                    core_skills="DevOps, Security, Python, Architecture",
                    proficiency="Lead",
                    is_active=True
                ),
                User(
                    username="john_dev",
                    email="john@bugflow.io",
                    hashed_password=get_password_hash("devpassword123"),
                    full_name="John Doe (Backend)",
                    role="DEVELOPER",
                    team="Backend Engineering",
                    core_skills="Python, PostgreSQL, Database, SQL, FastAPI, Redis",
                    proficiency="Senior",
                    is_active=True
                ),
                User(
                    username="alice_dev",
                    email="alice@bugflow.io",
                    hashed_password=get_password_hash("devpassword123"),
                    full_name="Alice Smith (Frontend)",
                    role="DEVELOPER",
                    team="Frontend UI",
                    core_skills="React, CSS, JavaScript, HTML, Tailwind, UI",
                    proficiency="Senior",
                    is_active=True
                ),
                User(
                    username="bruce_tester",
                    email="bruce@bugflow.io",
                    hashed_password=get_password_hash("testerpassword123"),
                    full_name="Bruce Wayne (Tester)",
                    role="TESTER",
                    team="QA Testing",
                    core_skills="Selenium, Pytest, Cypress, QA, API Testing",
                    proficiency="Mid",
                    is_active=True
                ),
                User(
                    username="tina_triager",
                    email="tina@bugflow.io",
                    hashed_password=get_password_hash("triagerpassword123"),
                    full_name="Tina Turner (Triager)",
                    role="TRIAGER",
                    team="Product Operations",
                    core_skills="Agile, Triage, Backlog Grooming, Jira",
                    proficiency="Senior",
                    is_active=True
                ),
                User(
                    username="sam_stakeholder",
                    email="sam@bugflow.io",
                    hashed_password=get_password_hash("stakeholderpassword123"),
                    full_name="Sam Altman (Stakeholder)",
                    role="STAKEHOLDER",
                    team="Executive Leadership",
                    core_skills="Business Analysis, Metrics, Reporting",
                    proficiency="Lead",
                    is_active=True
                ),
            ]
            db.add_all(users)
            db.commit()

            # 3. Project
            project = Project(
                project_name="BugFlow Platform Core",
                codebase="github.com/bugflow-org/core-platform",
                development_cycle="2-Week Agile Sprint",
                created_at=datetime.utcnow() - timedelta(days=20)
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            # 4. Sprints
            sprint1 = Sprint(
                project_id=project.project_id,
                sprint_name="Sprint 1 - Foundation",
                goal="Establish core authentication, database schemas, and baseline APIs",
                start_date=datetime.utcnow() - timedelta(days=20),
                end_date=datetime.utcnow() - timedelta(days=6),
                status="COMPLETED",
                velocity=3.0,
                created_at=datetime.utcnow() - timedelta(days=20)
            )
            sprint2 = Sprint(
                project_id=project.project_id,
                sprint_name="Sprint 2 - Workflow & Collaboration",
                goal="Deploy state machine, discussion threads, and analytics engine",
                start_date=datetime.utcnow() - timedelta(days=5),
                end_date=datetime.utcnow() + timedelta(days=9),
                status="ACTIVE",
                velocity=0.0,
                created_at=datetime.utcnow() - timedelta(days=5)
            )
            db.add_all([sprint1, sprint2])
            db.commit()

        # Query references
        user_dict = {u.username: u for u in db.query(User).all()}
        cat_dict = {c.category_name: c for c in db.query(BugCategory).all()}
        project = db.query(Project).first()
        sprint1 = db.query(Sprint).filter(Sprint.sprint_name.like("%Sprint 1%")).first()
        sprint2 = db.query(Sprint).filter(Sprint.sprint_name.like("%Sprint 2%")).first()

        # 5. Releases (Module 4)
        if db.query(Release).count() == 0 and project:
            release1 = Release(
                project_id=project.project_id,
                version_name="v1.0.0-GA",
                release_date=datetime.utcnow() + timedelta(days=7),
                status="IN_PROGRESS",
                release_notes="BugFlow General Availability core platform release",
                created_at=datetime.utcnow() - timedelta(days=10)
            )
            release2 = Release(
                project_id=project.project_id,
                version_name="v1.1.0-Scale",
                release_date=datetime.utcnow() + timedelta(days=25),
                status="PLANNING",
                release_notes="High-scale 50k+ issue optimization & mobile portal sync",
                created_at=datetime.utcnow() - timedelta(days=5)
            )
            db.add_all([release1, release2])
            db.commit()

        release1 = db.query(Release).filter(Release.version_name == "v1.0.0-GA").first()

        # 6. Seed Issues if missing
        if db.query(Issue).count() == 0 and project and cat_dict and user_dict:
            now = datetime.utcnow()
            sample_issues = [
                {
                    "title": "Database connection pool timeout under load",
                    "description": "PostgreSQL pool drops idle connections during peak queries.",
                    "issue_type": "BUG",
                    "reproduction_steps": "1. Run 100 concurrent requests\n2. Observe connection timeout in log",
                    "severity": "CRITICAL",
                    "category": cat_dict.get("Database Error", list(cat_dict.values())[0]),
                    "reporter": user_dict["bruce_tester"],
                    "assignee": user_dict["john_dev"],
                    "sprint": sprint1,
                    "release": release1,
                    "status": "RESOLVED",
                    "dev_stage": "Staging",
                    "affected_modules": "Database, ConnectionPool",
                    "environment_details": "PostgreSQL 15, Ubuntu 22.04",
                    "tags": "performance, database, postgresql",
                    "code_references": "commit: 4a7c18d",
                    "estimated_effort": 3.0,
                    "created_at": now - timedelta(days=12),
                    "resolved_at": now - timedelta(days=10),
                },
                {
                    "title": "Login password crash with special characters",
                    "description": "Unicode characters in passwords trigger unhandled 500 error in auth router.",
                    "issue_type": "BUG",
                    "reproduction_steps": "1. Input password with unicode emoji\n2. Click Submit\n3. 500 Internal Error",
                    "severity": "CRITICAL",
                    "category": cat_dict.get("Security Vulnerability", list(cat_dict.values())[0]),
                    "reporter": user_dict["bruce_tester"],
                    "assignee": user_dict["john_dev"],
                    "sprint": sprint2,
                    "release": release1,
                    "status": "IN_PROGRESS",
                    "dev_stage": "Development",
                    "affected_modules": "Auth, Login",
                    "environment_details": "Chrome 122, macOS Sonoma",
                    "tags": "auth, security, unicode",
                    "code_references": "app/auth.py:45",
                    "estimated_effort": 2.0,
                    "created_at": now - timedelta(days=3),
                    "resolved_at": None,
                },
                {
                    "title": "CSS button alignment glitch on mobile viewport",
                    "description": "Submit button overlaps with bottom navigation bar on screens under 480px width.",
                    "issue_type": "UI_GLITCH",
                    "reproduction_steps": "1. Open on iPhone 13\n2. Navigate to Issue Form\n3. Inspect footer overlapping",
                    "severity": "MINOR",
                    "category": cat_dict.get("UI Glitch", list(cat_dict.values())[0]),
                    "reporter": user_dict["bruce_tester"],
                    "assignee": user_dict["alice_dev"],
                    "sprint": sprint2,
                    "release": release1,
                    "status": "TRIAGED",
                    "dev_stage": "Testing",
                    "affected_modules": "UI, Responsive Layout",
                    "environment_details": "iOS 17 Safari, iPhone 14",
                    "tags": "frontend, responsive, css",
                    "code_references": "app/static/index.html:150",
                    "estimated_effort": 1.0,
                    "created_at": now - timedelta(days=2),
                    "resolved_at": None,
                },
                {
                    "title": "API Gateway returns 502 on invalid bearer token",
                    "description": "Expired JWT tokens should return 401 Unauthorized instead of gateway bad response.",
                    "issue_type": "BUG",
                    "reproduction_steps": "1. Send expired JWT in Authorization header\n2. Gateway throws 502",
                    "severity": "MAJOR",
                    "category": cat_dict.get("API Gateway", list(cat_dict.values())[0]),
                    "reporter": user_dict["bruce_tester"],
                    "assignee": user_dict["john_dev"],
                    "sprint": sprint2,
                    "release": release1,
                    "status": "QA_VERIFICATION",
                    "dev_stage": "Testing",
                    "affected_modules": "API Gateway, Auth Middleware",
                    "environment_details": "Docker Linux, FastAPI Gateway",
                    "tags": "gateway, jwt, api",
                    "code_references": "app/auth.py:28",
                    "estimated_effort": 2.0,
                    "created_at": now - timedelta(days=4),
                    "resolved_at": None,
                },
                {
                    "title": "Automated recurring billing tax line discrepancy",
                    "description": "Cent rounding issue causes 1-cent variance on recurring invoice line items.",
                    "issue_type": "FEATURE_REQUEST",
                    "reproduction_steps": "1. Generate quarterly invoice with 3 tax lines\n2. Sum is $0.01 higher than subtotal",
                    "severity": "MAJOR",
                    "category": cat_dict.get("Backend Logic", list(cat_dict.values())[0]),
                    "reporter": user_dict["tina_triager"],
                    "assignee": None,
                    "sprint": None,
                    "release": release1,
                    "status": "REPORTED",
                    "dev_stage": "Development",
                    "affected_modules": "Billing, InvoiceService",
                    "environment_details": "Python 3.10 Backend",
                    "tags": "billing, accounting",
                    "code_references": "",
                    "estimated_effort": 3.0,
                    "created_at": now - timedelta(days=1),
                    "resolved_at": None,
                },
                {
                    "title": "Production memory leak in background worker queue",
                    "description": "Worker memory gradually rises over 72 hours until killed by OOM killer in Prod.",
                    "issue_type": "TECH_DEBT",
                    "reproduction_steps": "1. Monitor Celery pods in production\n2. Memory increases steadily over 3 days",
                    "severity": "CRITICAL",
                    "category": cat_dict.get("Backend Logic", list(cat_dict.values())[0]),
                    "reporter": user_dict["admin"],
                    "assignee": None,
                    "sprint": None,
                    "release": None,
                    "status": "REPORTED",
                    "dev_stage": "Production",
                    "environment_details": "Linux Ubuntu 22.04 (Production Cluster us-east-1)",
                    "tags": "memory, devops, worker",
                    "code_references": "",
                    "estimated_effort": 5.0,
                    "created_at": now - timedelta(hours=8),
                    "resolved_at": None,
                },
            ]

            for item in sample_issues:
                cat = item["category"]
                score, priority, _, _ = calculate_priority(item["severity"], cat.urgency, cat.category_name)
                issue = Issue(
                    project_id=project.project_id,
                    reporter_id=item["reporter"].id,
                    assignee_id=item["assignee"].id if item.get("assignee") else None,
                    category_id=cat.category_id,
                    sprint_id=item["sprint"].sprint_id if item.get("sprint") else None,
                    release_id=item["release"].release_id if item.get("release") else None,
                    title=item["title"],
                    description=item["description"],
                    issue_type=item.get("issue_type", "BUG"),
                    reproduction_steps=item.get("reproduction_steps", ""),
                    severity=item["severity"],
                    priority=priority,
                    status=item["status"],
                    dev_stage=item.get("dev_stage", "Development"),
                    affected_modules=item.get("affected_modules", ""),
                    environment_details=item.get("environment_details", ""),
                    tags=item.get("tags", ""),
                    code_references=item.get("code_references", ""),
                    estimated_effort=item.get("estimated_effort", 1.0),
                    priority_score=score,
                    created_at=item["created_at"],
                    updated_at=item["created_at"],
                    resolved_at=item.get("resolved_at")
                )
                db.add(issue)
                db.commit()
                db.refresh(issue)

                db.add(AuditLog(
                    issue_id=issue.id,
                    user_id=item["reporter"].id,
                    action="CREATED",
                    field_name="status",
                    old_value=None,
                    new_value="REPORTED",
                    timestamp=item["created_at"]
                ))
                db.commit()

        # 7. Seed PDF Page 10 Schema Entities
        if db.query(HistoricalBugFix).count() == 0 and user_dict:
            fixes = [
                HistoricalBugFix(
                    dev_id=user_dict["john_dev"].id,
                    past_fixes="Resolved PostgreSQL idle connection drop in DB pool",
                    code_changes="Increased pool_pre_ping=True and pool_recycle=1800 in database.py",
                    resolution_time="1.5 days"
                ),
                HistoricalBugFix(
                    dev_id=user_dict["john_dev"].id,
                    past_fixes="Fixed JWT expiration unhandled 502 to 401 Unauthorized",
                    code_changes="Added jwt.ExpiredSignatureError handler in auth middleware",
                    resolution_time="2.0 days"
                ),
                HistoricalBugFix(
                    dev_id=user_dict["alice_dev"].id,
                    past_fixes="Corrected mobile viewport button z-index and flex wrapping",
                    code_changes="Updated Tailwind responsive classes sm:flex-row pb-safe",
                    resolution_time="0.5 days"
                ),
            ]
            db.add_all(fixes)
            db.commit()

        if db.query(UserTriageInsight).count() == 0 and user_dict:
            insights = [
                UserTriageInsight(
                    dev_id=user_dict["john_dev"].id,
                    bug_score=94,
                    team_efficiency="High (0.85 MTTR improvement)",
                    backlog_progression="Ahead of schedule in Sprint 2"
                ),
                UserTriageInsight(
                    dev_id=user_dict["alice_dev"].id,
                    bug_score=89,
                    team_efficiency="Optimal (100% UI bug fix rate)",
                    backlog_progression="On Track"
                ),
            ]
            db.add_all(insights)
            db.commit()

        if db.query(BugFlowUserPortal).count() == 0:
            portals = [
                BugFlowUserPortal(portal_type="Web Dashboard", portal_name="BugFlow QA & Developer Dashboard", version="1.0.0"),
                BugFlowUserPortal(portal_type="Developer API", portal_name="BugFlow REST API & Swagger Explorer", version="1.0.0"),
                BugFlowUserPortal(portal_type="Reporter Mobile App", portal_name="BugFlow Triager & Reporter Portal", version="1.0.0"),
                BugFlowUserPortal(portal_type="CI/CD Console", portal_name="BugFlow Git & Pipeline Integration Hook", version="1.0.0"),
            ]
            db.add_all(portals)
            db.commit()

        if db.query(IndividualBugSaga).count() == 0:
            sagas = [
                IndividualBugSaga(
                    issue_ids="1, 2, 4",
                    feature_request_ids="5",
                    dev_stage="In Progress"
                ),
                IndividualBugSaga(
                    issue_ids="3",
                    feature_request_ids="",
                    dev_stage="Triaged"
                )
            ]
            db.add_all(sagas)
            db.commit()

        if db.query(ReporterIssueTracking).count() == 0 and user_dict:
            trackers = [
                ReporterIssueTracking(
                    reporter_id=user_dict["bruce_tester"].id,
                    related_case="SEC-AUTH-001",
                    expected_resolution="Graceful 401 on Unicode/Special passwords",
                    progress="Under Developer John Doe review"
                ),
                ReporterIssueTracking(
                    reporter_id=user_dict["tina_triager"].id,
                    related_case="BILL-TAX-102",
                    expected_resolution="Bankers rounding formula applied across all invoices",
                    progress="Backlog queued for Sprint 3"
                ),
            ]
            db.add_all(trackers)
            db.commit()

        print("BugFlow Database seeding check complete!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()