from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="DEVELOPER")  # ADMIN, DEVELOPER, TESTER, TRIAGER, STAKEHOLDER
    team = Column(String(100), nullable=True, default="Engineering")
    core_skills = Column(String(255), nullable=True, default="")
    proficiency = Column(String(50), nullable=True, default="Mid")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    reported_issues = relationship("Issue", foreign_keys="Issue.reporter_id", back_populates="reporter")
    assigned_issues = relationship("Issue", foreign_keys="Issue.assignee_id", back_populates="assignee")
    comments = relationship("Comment", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    historical_fixes = relationship("HistoricalBugFix", back_populates="developer")
    triage_insights = relationship("UserTriageInsight", back_populates="developer")


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_name = Column(String(255), unique=True, index=True, nullable=False)
    codebase = Column(String(255), nullable=True, default="")
    development_cycle = Column(String(100), nullable=True, default="2-Week Agile Sprint")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    issues = relationship("Issue", back_populates="project", cascade="all, delete-orphan")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan")
    releases = relationship("Release", back_populates="project", cascade="all, delete-orphan")


class BugCategory(Base):
    __tablename__ = "bug_categories"

    category_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_name = Column(String(100), unique=True, nullable=False)
    urgency = Column(String(50), nullable=False, default="Medium Urgency")  # High Urgency, Medium Urgency, Low Urgency

    issues = relationship("Issue", back_populates="category")


class Sprint(Base):
    __tablename__ = "sprints"

    sprint_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    sprint_name = Column(String(255), nullable=False)
    goal = Column(Text, nullable=True, default="")
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="PLANNING", nullable=False)  # PLANNING, ACTIVE, COMPLETED
    velocity = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="sprints")
    issues = relationship("Issue", back_populates="sprint")


class Release(Base):
    __tablename__ = "releases"

    release_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    version_name = Column(String(100), nullable=False)
    release_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="PLANNING", nullable=False)  # PLANNING, IN_PROGRESS, RELEASED
    release_notes = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="releases")
    issues = relationship("Issue", back_populates="release")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("bug_categories.category_id"), nullable=False)
    sprint_id = Column(Integer, ForeignKey("sprints.sprint_id"), nullable=True, index=True)
    release_id = Column(Integer, ForeignKey("releases.release_id"), nullable=True, index=True)
    merged_into_id = Column(Integer, ForeignKey("issues.id"), nullable=True)

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    issue_type = Column(String(50), nullable=False, default="BUG")  # BUG, FEATURE_REQUEST, ENHANCEMENT, SUPPORT_TICKET, TECH_DEBT
    reproduction_steps = Column(Text, nullable=True, default="")
    severity = Column(String(50), nullable=False, default="MINOR")  # CRITICAL, MAJOR, MINOR, TRIVIAL
    priority = Column(String(50), nullable=False, default="MEDIUM")  # URGENT, HIGH, MEDIUM, LOW
    status = Column(String(50), nullable=False, default="REPORTED")  # REPORTED, TRIAGED, IN_PROGRESS, CODE_REVIEW, QA_VERIFICATION, RESOLVED, CLOSED
    dev_stage = Column(String(50), nullable=False, default="Development")  # Development, Testing, Staging, Production
    affected_modules = Column(String(255), nullable=True, default="")
    environment_details = Column(String(255), nullable=True, default="")
    tags = Column(String(255), nullable=True, default="")
    code_references = Column(Text, nullable=True, default="")
    estimated_effort = Column(Float, nullable=False, default=1.0)
    priority_score = Column(Float, nullable=False, default=4.0)

    # Escalation & Approval
    is_escalated = Column(Boolean, default=False, nullable=False)
    escalation_reason = Column(Text, nullable=True, default="")
    is_approved = Column(Boolean, default=False, nullable=False)
    approval_notes = Column(Text, nullable=True, default="")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Composite indexes for high performance querying
    __table_args__ = (
        Index("ix_issues_project_status", "project_id", "status"),
        Index("ix_issues_assignee_status", "assignee_id", "status"),
        Index("ix_issues_created_at_desc", "created_at"),
    )

    # Relationships
    project = relationship("Project", back_populates="issues")
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reported_issues")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_issues")
    category = relationship("BugCategory", back_populates="issues")
    sprint = relationship("Sprint", back_populates="issues")
    release = relationship("Release", back_populates="issues")
    comments = relationship("Comment", back_populates="issue", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="issue", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="issue", cascade="all, delete-orphan")
    assignments = relationship("IssueAssignment", back_populates="issue", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    issue = relationship("Issue", back_populates="comments")
    user = relationship("User", back_populates="comments")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    issue = relationship("Issue", back_populates="attachments")
    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    issue = relationship("Issue", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")


# =========================================================================
# Database Entities from Specification Document (PDF Page 10 Schema)
# =========================================================================

class IndividualBugSaga(Base):
    __tablename__ = "individual_bug_sagas"

    saga_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    issue_ids = Column(String(255), nullable=True, default="")
    feature_request_ids = Column(String(255), nullable=True, default="")
    dev_stage = Column(String(50), nullable=False, default="Reported")  # 'Reported', 'Triaged', 'In Progress', 'Resolved'


class ReporterIssueTracking(Base):
    __tablename__ = "reporter_issue_tracking"

    tracking_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    related_case = Column(String(255), nullable=True, default="")
    expected_resolution = Column(String(255), nullable=True, default="")
    progress = Column(String(100), nullable=True, default="Pending")

    reporter = relationship("User")


class IssueAssignment(Base):
    __tablename__ = "issue_assignments"

    assignment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bug_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    title = Column(String(255), nullable=False)
    estimated_effort = Column(String(50), nullable=True, default="1d")
    priority = Column(String(50), nullable=False, default="High")  # 'High', 'Medium', 'Low'

    issue = relationship("Issue", back_populates="assignments")


class HistoricalBugFix(Base):
    __tablename__ = "historical_bug_fixes"

    fix_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dev_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    past_fixes = Column(String(255), nullable=False)
    code_changes = Column(Text, nullable=True, default="")
    resolution_time = Column(String(50), nullable=True, default="2.5 days")

    developer = relationship("User", back_populates="historical_fixes")


class UserTriageInsight(Base):
    __tablename__ = "user_triage_insights"

    triage_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dev_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bug_score = Column(Integer, default=85)
    team_efficiency = Column(Text, nullable=True, default="High")
    backlog_progression = Column(Text, nullable=True, default="On Track")

    developer = relationship("User", back_populates="triage_insights")


class BugFlowUserPortal(Base):
    __tablename__ = "bugflow_user_portals"

    portal_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portal_type = Column(String(50), nullable=False, default="Web Dashboard")  # 'Web Dashboard', 'Developer API', 'Reporter Mobile App', 'CI/CD Console'
    portal_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False, default="1.0.0")