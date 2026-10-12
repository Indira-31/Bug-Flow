import re
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator

# ----------------- User Schemas -----------------
class UserBase(BaseModel):
    username: str
    email: str
    full_name: str
    role: str = "DEVELOPER"  # ADMIN, DEVELOPER, TESTER, TRIAGER, STAKEHOLDER
    team: Optional[str] = "Engineering"
    core_skills: Optional[str] = ""
    proficiency: Optional[str] = "Mid"

    @field_validator("email")
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Invalid email format")
        return clean.lower()

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ----------------- Project Schemas -----------------
class ProjectBase(BaseModel):
    project_name: str
    codebase: Optional[str] = ""
    development_cycle: Optional[str] = "2-Week Agile Sprint"

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    project_id: int
    created_at: datetime
    issue_count: Optional[int] = 0
    model_config = ConfigDict(from_attributes=True)


# ----------------- Bug Category Schemas -----------------
class BugCategoryBase(BaseModel):
    category_name: str
    urgency: str = "Medium Urgency"

class BugCategoryCreate(BugCategoryBase):
    pass

class BugCategoryResponse(BugCategoryBase):
    category_id: int
    model_config = ConfigDict(from_attributes=True)


# ----------------- Sprint Schemas -----------------
class SprintBase(BaseModel):
    project_id: int
    sprint_name: str
    goal: Optional[str] = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "PLANNING"

class SprintCreate(SprintBase):
    pass

class SprintResponse(SprintBase):
    sprint_id: int
    velocity: float = 0.0
    created_at: datetime
    issue_count: Optional[int] = 0
    resolved_count: Optional[int] = 0
    model_config = ConfigDict(from_attributes=True)


# ----------------- Release Schemas (Module 4) -----------------
class ReleaseBase(BaseModel):
    project_id: int
    version_name: str
    release_date: Optional[datetime] = None
    status: str = "PLANNING"  # PLANNING, IN_PROGRESS, RELEASED
    release_notes: Optional[str] = ""

class ReleaseCreate(ReleaseBase):
    pass

class ReleaseResponse(ReleaseBase):
    release_id: int
    created_at: datetime
    total_issues: Optional[int] = 0
    resolved_issues: Optional[int] = 0
    completion_rate_percentage: Optional[float] = 0.0
    model_config = ConfigDict(from_attributes=True)

class ReleaseReadinessResponse(BaseModel):
    release_id: int
    version_name: str
    status: str
    readiness_status: str  # "RELEASE_READY", "AT_RISK", "BLOCKED"
    readiness_percentage: float
    total_issues: int
    resolved_issues: int
    open_blockers_count: int  # Critical / Major open issues
    blocking_issues: List[Dict[str, Any]] = []


# ----------------- Collaboration Schemas -----------------
class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    issue_id: int
    user_id: int
    content: str
    created_at: datetime
    user: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)

class AttachmentResponse(BaseModel):
    id: int
    issue_id: int
    user_id: int
    filename: str
    file_size: int
    content_type: str
    created_at: datetime
    user: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: int
    issue_id: int
    user_id: Optional[int] = None
    action: str
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: datetime
    user: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)


# ----------------- Issue Schemas -----------------
class IssueBase(BaseModel):
    project_id: int
    category_id: int
    title: str
    description: str
    issue_type: str = "BUG"  # BUG, FEATURE_REQUEST, ENHANCEMENT, SUPPORT_TICKET, TECH_DEBT
    reproduction_steps: Optional[str] = ""
    severity: str = "MINOR"  # CRITICAL, MAJOR, MINOR, TRIVIAL
    priority: Optional[str] = None  # Auto-calculated if omitted
    dev_stage: str = "Development"
    affected_modules: Optional[str] = ""
    environment_details: Optional[str] = ""
    tags: Optional[str] = ""
    code_references: Optional[str] = ""
    estimated_effort: float = 1.0
    assignee_id: Optional[int] = None
    sprint_id: Optional[int] = None
    release_id: Optional[int] = None

class IssueCreate(IssueBase):
    pass

class IssueUpdateStatus(BaseModel):
    status: str

class IssueAssign(BaseModel):
    assignee_id: Optional[int] = None

class IssueMergeRequest(BaseModel):
    duplicate_issue_id: int
    merge_reason: Optional[str] = "Identified as duplicate report"

class IssueEscalateRequest(BaseModel):
    reason: str
    target_priority: Optional[str] = "URGENT"

class IssueApproveRequest(BaseModel):
    approval_notes: Optional[str] = "Code verified and approved"

class IssueResponse(BaseModel):
    id: int
    project_id: int
    reporter_id: int
    assignee_id: Optional[int] = None
    category_id: int
    sprint_id: Optional[int] = None
    release_id: Optional[int] = None
    merged_into_id: Optional[int] = None
    title: str
    description: str
    issue_type: str = "BUG"
    reproduction_steps: Optional[str] = ""
    severity: str
    priority: str
    status: str
    dev_stage: str
    affected_modules: Optional[str] = ""
    environment_details: Optional[str] = ""
    tags: Optional[str] = ""
    code_references: Optional[str] = ""
    estimated_effort: float
    priority_score: float
    is_escalated: bool = False
    escalation_reason: Optional[str] = ""
    is_approved: bool = False
    approval_notes: Optional[str] = ""
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    reporter: Optional[UserResponse] = None
    assignee: Optional[UserResponse] = None
    category: Optional[BugCategoryResponse] = None
    sprint: Optional[SprintResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

class IssueDetailResponse(IssueResponse):
    comments: List[CommentResponse] = []
    attachments: List[AttachmentResponse] = []
    audit_logs: List[AuditLogResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ----------------- Duplicate Detection Schemas -----------------
class DuplicateCheckRequest(BaseModel):
    project_id: int
    title: str

class DuplicateMatchItem(BaseModel):
    id: int
    title: str
    similarity_score: float
    status: str
    severity: str

class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    threshold: float = 0.55
    matches: List[DuplicateMatchItem]


# ----------------- Smart Match & Triage Schemas -----------------
class TriageRecommendationRequest(BaseModel):
    title: str
    description: str
    severity: str = "MINOR"
    category_id: int
    affected_modules: Optional[str] = ""

class RecommendedDeveloper(BaseModel):
    user_id: int
    full_name: str
    username: str
    team: str
    core_skills: str
    active_tasks: int
    match_percentage: float
    rationale: str

class TriageRecommendationResponse(BaseModel):
    priority_score: float
    priority: str
    severity_weight: int
    urgency_weight: int
    recommended_developers: List[RecommendedDeveloper]


# ----------------- BugFlow AI Core Engine (PDF Page 10) -----------------
class AICoreAnalysisRequest(BaseModel):
    title: str
    description: str
    category_id: int
    severity: Optional[str] = "MINOR"
    code_diff: Optional[str] = ""
    project_context: Optional[str] = ""
    affected_modules: Optional[str] = ""

class ResolutionPathStep(BaseModel):
    step: int
    phase: str
    action: str
    suggested_tests: List[str]

class AICoreAnalysisResponse(BaseModel):
    # Inputs verified
    analyzed_title: str
    analyzed_severity: str
    ai_ethical_bias_passed: bool
    ethical_bias_report: str
    
    # Process
    categorization: str
    suggested_severity: str
    priority_score: float
    priority: str
    matched_historical_patterns: List[Dict[str, Any]]
    
    # Outputs (Page 10)
    personalized_resolution_path: List[ResolutionPathStep]
    developer_assignments: List[RecommendedDeveloper]
    automated_cicd_rollback_path: str
    cycle_insights: str


# ----------------- CI/CD Git Webhook Schemas -----------------
class GitWebhookPayload(BaseModel):
    commit_message: str
    commit_sha: Optional[str] = "HEAD"
    branch: Optional[str] = "main"
    author: Optional[str] = "CI/CD Bot"

class GitWebhookResponse(BaseModel):
    status: str
    matched_issues: List[int]
    message: str

class CICDPipelineWebhookPayload(BaseModel):
    pipeline_id: str
    issue_ids: List[int]
    stage: str  # "BUILD", "TEST", "DEPLOY"
    build_status: str  # "SUCCESS", "FAILED"
    details: Optional[str] = ""


# ----------------- Analytics & Quality Scorecard -----------------
class QualityMetricsResponse(BaseModel):
    total_bugs: int
    resolved_bugs: int
    closed_bugs: int
    open_bugs: int
    fix_rate_percentage: float
    mean_time_to_resolution_hours: float
    defect_leakage_rate_percentage: float
    backlog_health_score: float

class DefectTrendItem(BaseModel):
    date: str
    reported: int
    resolved: int

class DeveloperWorkloadItem(BaseModel):
    user_id: int
    full_name: str
    username: str
    team: str
    active_tasks: int
    completed_fixes: int
    average_mttr_hours: float


# ----------------- Specification Page 10 Database Entities Schemas -----------------
class IndividualBugSagaResponse(BaseModel):
    saga_id: int
    issue_ids: Optional[str] = ""
    feature_request_ids: Optional[str] = ""
    dev_stage: str
    model_config = ConfigDict(from_attributes=True)

class ReporterIssueTrackingResponse(BaseModel):
    tracking_id: int
    reporter_id: int
    related_case: Optional[str] = ""
    expected_resolution: Optional[str] = ""
    progress: Optional[str] = ""
    model_config = ConfigDict(from_attributes=True)

class IssueAssignmentResponse(BaseModel):
    assignment_id: int
    bug_id: int
    title: str
    estimated_effort: str
    priority: str
    model_config = ConfigDict(from_attributes=True)

class HistoricalBugFixResponse(BaseModel):
    fix_id: int
    dev_id: int
    past_fixes: str
    code_changes: Optional[str] = ""
    resolution_time: str
    model_config = ConfigDict(from_attributes=True)

class UserTriageInsightResponse(BaseModel):
    triage_id: int
    dev_id: int
    bug_score: int
    team_efficiency: str
    backlog_progression: str
    model_config = ConfigDict(from_attributes=True)

class BugFlowUserPortalResponse(BaseModel):
    portal_id: int
    portal_type: str
    portal_name: str
    version: str
    model_config = ConfigDict(from_attributes=True)


# ----------------- System Backup & Restore Schemas (Module 5) -----------------
class BackupRestoreResponse(BaseModel):
    status: str
    message: str
    timestamp: datetime
    backup_file: Optional[str] = None
    records_count: Optional[Dict[str, int]] = None

class RetentionPolicyResponse(BaseModel):
    policy_name: str
    archived_or_evaluated_records: int
    retention_period_days: int
    timestamp: datetime
    status: str