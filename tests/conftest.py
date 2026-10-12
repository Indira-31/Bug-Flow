import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.models import (
    User, Project, BugCategory, Sprint, Issue,
    HistoricalBugFix, UserTriageInsight, BugFlowUserPortal,
    IndividualBugSaga, ReporterIssueTracking
)
from app.auth import get_password_hash, create_access_token
from main import app

# Isolated Test SQLite Database
TEST_DB_URL = "sqlite:///./test_bugflow.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Seed Categories
    categories = [
        BugCategory(category_id=1, category_name="Security Vulnerability", urgency="High Urgency"),
        BugCategory(category_id=2, category_name="Database Error", urgency="High Urgency"),
        BugCategory(category_id=3, category_name="Backend Logic", urgency="Medium Urgency"),
        BugCategory(category_id=4, category_name="API Gateway", urgency="Medium Urgency"),
        BugCategory(category_id=5, category_name="UI Glitch", urgency="Low Urgency"),
    ]
    db.add_all(categories)

    # Seed Users for all 5 Roles
    users = [
        User(
            id=1,
            username="admin_user",
            email="admin@test.io",
            hashed_password=get_password_hash("testpass123"),
            full_name="Admin User",
            role="ADMIN",
            team="Platform Ops",
            core_skills="DevOps, Security, Python",
            proficiency="Lead",
            is_active=True
        ),
        User(
            id=2,
            username="john_dev",
            email="john@test.io",
            hashed_password=get_password_hash("testpass123"),
            full_name="John Doe",
            role="DEVELOPER",
            team="Backend",
            core_skills="Python, PostgreSQL, Database, SQL, FastAPI",
            proficiency="Senior",
            is_active=True
        ),
        User(
            id=3,
            username="alice_dev",
            email="alice@test.io",
            hashed_password=get_password_hash("testpass123"),
            full_name="Alice Smith",
            role="DEVELOPER",
            team="Frontend",
            core_skills="React, CSS, HTML, JavaScript, UI",
            proficiency="Senior",
            is_active=True
        ),
        User(
            id=4,
            username="bruce_tester",
            email="bruce@test.io",
            hashed_password=get_password_hash("testpass123"),
            full_name="Bruce Tester",
            role="TESTER",
            team="QA",
            core_skills="Pytest, Selenium, QA",
            proficiency="Mid",
            is_active=True
        ),
        User(
            id=5,
            username="tina_triager",
            email="tina@test.io",
            hashed_password=get_password_hash("testpass123"),
            full_name="Tina Triager",
            role="TRIAGER",
            team="Triage Ops",
            core_skills="Agile, Jira, Triage",
            proficiency="Senior",
            is_active=True
        ),
        User(
            id=6,
            username="sam_stakeholder",
            email="sam@test.io",
            hashed_password=get_password_hash("testpass123"),
            full_name="Sam Stakeholder",
            role="STAKEHOLDER",
            team="Executive",
            core_skills="Reporting, Business",
            proficiency="Lead",
            is_active=True
        ),
    ]
    db.add_all(users)

    # Seed Project
    project = Project(
        project_id=1,
        project_name="BugFlow Core Project",
        codebase="github.com/company/repo",
        development_cycle="2-Week Agile Sprint"
    )
    db.add(project)

    # Seed Sprint
    sprint = Sprint(
        sprint_id=1,
        project_id=1,
        sprint_name="Sprint 1 - Foundation",
        goal="Test Goal",
        status="ACTIVE"
    )
    db.add(sprint)

    # Seed an Issue
    issue = Issue(
        id=1,
        project_id=1,
        reporter_id=4,
        assignee_id=2,
        category_id=2,
        sprint_id=1,
        title="Existing Database connection timeout",
        description="Pool connection drops",
        severity="CRITICAL",
        priority="URGENT",
        status="REPORTED",
        dev_stage="Development",
        priority_score=12.0
    )
    db.add(issue)

    # Seed Page 10 tables
    portals = [
        BugFlowUserPortal(portal_type="Web Dashboard", portal_name="BugFlow Web Dashboard", version="1.0.0"),
        BugFlowUserPortal(portal_type="Developer API", portal_name="BugFlow REST API", version="1.0.0"),
        BugFlowUserPortal(portal_type="Reporter Mobile App", portal_name="BugFlow Mobile App", version="1.0.0"),
        BugFlowUserPortal(portal_type="CI/CD Console", portal_name="BugFlow CI/CD Console", version="1.0.0"),
    ]
    db.add_all(portals)

    fixes = [
        HistoricalBugFix(
            dev_id=2,
            past_fixes="Resolved PostgreSQL pool timeout leak",
            code_changes="Updated connection pool recycle",
            resolution_time="1.5 days"
        )
    ]
    db.add_all(fixes)

    insights = [
        UserTriageInsight(
            dev_id=2,
            bug_score=95,
            team_efficiency="High",
            backlog_progression="Optimal"
        )
    ]
    db.add_all(insights)

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def admin_headers():
    token = create_access_token(data={"sub": "1", "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_auth_headers(admin_headers):
    return admin_headers

@pytest.fixture
def dev_headers():
    token = create_access_token(data={"sub": "2", "role": "DEVELOPER"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def developer_auth_headers(dev_headers):
    return dev_headers

@pytest.fixture
def tester_headers():
    token = create_access_token(data={"sub": "4", "role": "TESTER"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def tester_auth_headers(tester_headers):
    return tester_headers

@pytest.fixture
def triager_headers():
    token = create_access_token(data={"sub": "5", "role": "TRIAGER"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def triager_auth_headers(triager_headers):
    return triager_headers

@pytest.fixture
def stakeholder_headers():
    token = create_access_token(data={"sub": "6", "role": "STAKEHOLDER"})
    return {"Authorization": f"Bearer {token}"}
