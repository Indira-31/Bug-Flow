from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import Issue, Project, BugCategory, User, AuditLog, Comment, Release
from app.schemas import (
    IssueCreate, IssueResponse, IssueDetailResponse, IssueUpdateStatus,
    IssueAssign, IssueMergeRequest, IssueEscalateRequest, IssueApproveRequest,
    DuplicateCheckRequest, DuplicateCheckResponse, DuplicateMatchItem,
    TriageRecommendationRequest, TriageRecommendationResponse,
    AICoreAnalysisRequest, AICoreAnalysisResponse
)
from app.auth import get_current_user, require_roles
from app.services.priority_service import calculate_priority, get_severity_weight, get_urgency_weight
from app.services.matching_service import match_developers_for_bug
from app.services.duplicate_service import check_duplicate_issues
from app.services.state_machine import transition_issue_status
from app.services.ai_core_service import analyze_issue_with_ai_core

router = APIRouter(prefix="/issues", tags=["Issues"])

@router.post("/", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
def create_issue(
    issue_in: IssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TESTER", "DEVELOPER", "TRIAGER"]))
):
    project = db.query(Project).filter(Project.project_id == issue_in.project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    category = db.query(BugCategory).filter(BugCategory.category_id == issue_in.category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug Category not found")

    # Smart Priority calculation
    priority_score, calculated_priority, _, _ = calculate_priority(
        severity=issue_in.severity,
        urgency_str=category.urgency,
        category_name=category.category_name
    )

    final_priority = issue_in.priority if issue_in.priority else calculated_priority

    issue = Issue(
        project_id=issue_in.project_id,
        reporter_id=current_user.id,
        assignee_id=issue_in.assignee_id,
        category_id=issue_in.category_id,
        sprint_id=issue_in.sprint_id,
        release_id=issue_in.release_id,
        title=issue_in.title.strip(),
        description=issue_in.description.strip(),
        issue_type=getattr(issue_in, "issue_type", "BUG") or "BUG",
        reproduction_steps=issue_in.reproduction_steps or "",
        severity=issue_in.severity.upper(),
        priority=final_priority.upper(),
        status="REPORTED",
        dev_stage=issue_in.dev_stage,
        affected_modules=issue_in.affected_modules or "",
        environment_details=issue_in.environment_details or "",
        tags=getattr(issue_in, "tags", "") or "",
        code_references=getattr(issue_in, "code_references", "") or "",
        estimated_effort=issue_in.estimated_effort,
        priority_score=priority_score,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)

    # Initial Audit Trail log
    audit_init = AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="CREATED",
        field_name="status",
        old_value=None,
        new_value="REPORTED",
        timestamp=datetime.utcnow()
    )
    db.add(audit_init)
    db.commit()

    return issue

@router.get("/", response_model=List[IssueResponse])
def list_issues(
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    sprint_id: Optional[int] = Query(None),
    release_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Issue)

    if project_id is not None:
        query = query.filter(Issue.project_id == project_id)
    if status:
        query = query.filter(Issue.status == status.upper())
    if severity:
        query = query.filter(Issue.severity == severity.upper())
    if issue_type:
        query = query.filter(Issue.issue_type == issue_type.upper())
    if tags:
        query = query.filter(Issue.tags.ilike(f"%{tags.strip()}%"))
    if assignee_id is not None:
        query = query.filter(Issue.assignee_id == assignee_id)
    if sprint_id is not None:
        query = query.filter(Issue.sprint_id == sprint_id)
    if release_id is not None:
        query = query.filter(Issue.release_id == release_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Issue.title.ilike(term), Issue.description.ilike(term)))

    return query.order_by(Issue.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{id}", response_model=IssueDetailResponse)
def get_issue(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue

@router.patch("/{id}/status", response_model=IssueResponse)
def update_issue_status(
    id: int,
    status_update: IssueUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVELOPER", "TESTER"]))
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    
    updated_issue = transition_issue_status(db, issue, status_update.status, current_user)
    return updated_issue

@router.patch("/{id}/assign", response_model=IssueResponse)
def assign_issue(
    id: int,
    assign_in: IssueAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TRIAGER", "DEVELOPER"]))
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    old_assignee = issue.assignee.full_name if issue.assignee else "Unassigned"

    if assign_in.assignee_id:
        target_dev = db.query(User).filter(User.id == assign_in.assignee_id).first()
        if not target_dev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target developer not found")
        new_assignee = target_dev.full_name
        issue.assignee_id = target_dev.id
    else:
        new_assignee = "Unassigned"
        issue.assignee_id = None

    issue.updated_at = datetime.utcnow()

    # Immutable Audit Log
    db.add(AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="ASSIGNMENT",
        field_name="assignee_id",
        old_value=old_assignee,
        new_value=new_assignee,
        timestamp=datetime.utcnow()
    ))
    db.commit()
    db.refresh(issue)
    return issue

@router.post("/{id}/merge", response_model=IssueResponse)
def merge_issue(
    id: int,
    merge_in: IssueMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TRIAGER", "DEVELOPER"]))
):
    """
    Module 1: Handle duplicate issue merging and audit trail maintenance.
    Closes duplicate issue and marks it merged into the primary issue.
    """
    primary_issue = db.query(Issue).filter(Issue.id == id).first()
    if not primary_issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Primary issue not found")

    duplicate_issue = db.query(Issue).filter(Issue.id == merge_in.duplicate_issue_id).first()
    if not duplicate_issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Duplicate issue to merge not found")

    if primary_issue.id == duplicate_issue.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot merge an issue into itself")

    # Copy comments from duplicate to primary
    dup_comments = db.query(Comment).filter(Comment.issue_id == duplicate_issue.id).all()
    for c in dup_comments:
        db.add(Comment(
            issue_id=primary_issue.id,
            user_id=c.user_id,
            content=f"[Merged from #{duplicate_issue.id}]: {c.content}",
            created_at=datetime.utcnow()
        ))

    # Mark duplicate as merged and closed
    duplicate_issue.merged_into_id = primary_issue.id
    duplicate_issue.status = "CLOSED"
    duplicate_issue.updated_at = datetime.utcnow()

    db.add(AuditLog(
        issue_id=duplicate_issue.id,
        user_id=current_user.id,
        action="MERGED_INTO",
        field_name="merged_into_id",
        old_value=None,
        new_value=f"Merged into #{primary_issue.id} ({merge_in.merge_reason})",
        timestamp=datetime.utcnow()
    ))

    # Audit log on primary
    db.add(AuditLog(
        issue_id=primary_issue.id,
        user_id=current_user.id,
        action="MERGE_RECEIVED",
        field_name="merged_from_id",
        old_value=None,
        new_value=f"Merged duplicate #{duplicate_issue.id} ({duplicate_issue.title})",
        timestamp=datetime.utcnow()
    ))

    primary_issue.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(primary_issue)
    return primary_issue

@router.post("/{id}/escalate", response_model=IssueResponse)
def escalate_issue(
    id: int,
    payload: IssueEscalateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TESTER", "TRIAGER"]))
):
    """
    Module 3: Support issue escalation workflows.
    Elevates issue priority and flags as escalated with audit logging.
    """
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    old_priority = issue.priority
    issue.is_escalated = True
    issue.escalation_reason = payload.reason
    issue.priority = payload.target_priority or "URGENT"
    issue.priority_score = max(issue.priority_score, 12.0)
    issue.updated_at = datetime.utcnow()

    db.add(AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="ESCALATED",
        field_name="priority",
        old_value=old_priority,
        new_value=f"{issue.priority} - Reason: {payload.reason}",
        timestamp=datetime.utcnow()
    ))
    db.commit()
    db.refresh(issue)
    return issue

@router.post("/{id}/approve", response_model=IssueResponse)
def approve_issue(
    id: int,
    payload: IssueApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVELOPER", "TESTER"]))
):
    """
    Module 3: Support approval workflows.
    Approves review/verification stages and advances workflow state.
    """
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    old_status = issue.status
    if issue.status == "CODE_REVIEW":
        next_status = "QA_VERIFICATION"
    elif issue.status == "QA_VERIFICATION":
        next_status = "RESOLVED"
        issue.resolved_at = datetime.utcnow()
    else:
        next_status = issue.status

    issue.is_approved = True
    issue.approval_notes = payload.approval_notes
    issue.status = next_status
    issue.updated_at = datetime.utcnow()

    db.add(AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="APPROVAL",
        field_name="status",
        old_value=old_status,
        new_value=f"Approved to {next_status} by {current_user.full_name}: {payload.approval_notes}",
        timestamp=datetime.utcnow()
    ))
    db.commit()
    db.refresh(issue)
    return issue

@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
def check_duplicates(
    payload: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    matches = check_duplicate_issues(db, payload.project_id, payload.title, threshold=0.55)
    match_items = [
        DuplicateMatchItem(
            id=m["id"],
            title=m["title"],
            similarity_score=m["similarity_score"],
            status=m["status"],
            severity=m["severity"]
        )
        for m in matches
    ]
    return DuplicateCheckResponse(
        is_duplicate=len(matches) > 0,
        threshold=0.55,
        matches=match_items
    )

@router.post("/triage-recommendation", response_model=TriageRecommendationResponse)
def triage_recommendation(
    payload: TriageRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = db.query(BugCategory).filter(BugCategory.category_id == payload.category_id).first()
    urgency_str = category.urgency if category else "Medium Urgency"
    category_name = category.category_name if category else ""

    score, priority, sev_weight, urg_weight = calculate_priority(
        severity=payload.severity,
        urgency_str=urgency_str,
        category_name=category_name
    )

    recommended_devs = match_developers_for_bug(
        db=db,
        title=payload.title,
        description=payload.description,
        affected_modules=payload.affected_modules or ""
    )

    return TriageRecommendationResponse(
        priority_score=score,
        priority=priority,
        severity_weight=sev_weight,
        urgency_weight=urg_weight,
        recommended_developers=recommended_devs
    )

@router.post("/ai-core-analysis", response_model=AICoreAnalysisResponse)
def ai_core_analysis(
    payload: AICoreAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Page 10 AI Core Engine pipeline:
    Analyzes issue report, code diff, historical patterns, and developer profiles.
    """
    result = analyze_issue_with_ai_core(
        db=db,
        title=payload.title,
        description=payload.description,
        category_id=payload.category_id,
        severity=payload.severity or "MINOR",
        code_diff=payload.code_diff or "",
        project_context=payload.project_context or "",
        affected_modules=payload.affected_modules or ""
    )
    return result

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_issue(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"]))
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    db.delete(issue)
    db.commit()
    return None