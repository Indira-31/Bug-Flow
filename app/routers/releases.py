from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Release, Issue, Project, User, AuditLog
from app.schemas import ReleaseCreate, ReleaseResponse, ReleaseReadinessResponse, IssueResponse
from app.auth import get_current_user, require_roles

router = APIRouter(prefix="/releases", tags=["Releases & Milestones"])

@router.post("/", response_model=ReleaseResponse, status_code=status.HTTP_201_CREATED)
def create_release(
    release_in: ReleaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TRIAGER"]))
):
    project = db.query(Project).filter(Project.project_id == release_in.project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    new_release = Release(
        project_id=release_in.project_id,
        version_name=release_in.version_name.strip(),
        release_date=release_in.release_date,
        status=release_in.status.upper(),
        release_notes=release_in.release_notes or "",
        created_at=datetime.utcnow()
    )
    db.add(new_release)
    db.commit()
    db.refresh(new_release)
    new_release.total_issues = 0
    new_release.resolved_issues = 0
    new_release.completion_rate_percentage = 0.0
    return new_release

@router.get("/", response_model=List[ReleaseResponse])
def list_releases(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Release)
    if project_id:
        query = query.filter(Release.project_id == project_id)
    releases = query.order_by(Release.created_at.desc()).all()

    for r in releases:
        issues = db.query(Issue).filter(Issue.release_id == r.release_id).all()
        total = len(issues)
        resolved = sum(1 for i in issues if i.status in ["RESOLVED", "CLOSED"])
        r.total_issues = total
        r.resolved_issues = resolved
        r.completion_rate_percentage = round((resolved / total * 100), 1) if total > 0 else 0.0

    return releases

@router.post("/{id}/assign-issue/{issue_id}", response_model=IssueResponse)
def assign_issue_to_release(
    id: int,
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TRIAGER", "DEVELOPER"]))
):
    release = db.query(Release).filter(Release.release_id == id).first()
    if not release:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release not found")

    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    old_rel = issue.release.version_name if issue.release else "None"
    issue.release_id = release.release_id
    issue.updated_at = datetime.utcnow()

    db.add(AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="RELEASE_ASSIGN",
        field_name="release_id",
        old_value=old_rel,
        new_value=release.version_name,
        timestamp=datetime.utcnow()
    ))
    db.commit()
    db.refresh(issue)
    return issue

@router.get("/{id}/readiness", response_model=ReleaseReadinessResponse)
def get_release_readiness(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Module 4: Monitor issue completion rates and release readiness metrics.
    """
    release = db.query(Release).filter(Release.release_id == id).first()
    if not release:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release not found")

    issues = db.query(Issue).filter(Issue.release_id == release.release_id).all()
    total = len(issues)
    resolved = sum(1 for i in issues if i.status in ["RESOLVED", "CLOSED"])
    completion_rate = round((resolved / total * 100), 1) if total > 0 else 100.0

    blockers = [
        {"id": i.id, "title": i.title, "severity": i.severity, "status": i.status}
        for i in issues
        if i.status not in ["RESOLVED", "CLOSED"] and i.severity in ["CRITICAL", "MAJOR"]
    ]

    if len(blockers) == 0 and completion_rate >= 80.0:
        readiness_status = "RELEASE_READY"
    elif len(blockers) > 0 and len(blockers) <= 2:
        readiness_status = "AT_RISK"
    else:
        readiness_status = "BLOCKED" if len(blockers) > 2 else "AT_RISK"

    return ReleaseReadinessResponse(
        release_id=release.release_id,
        version_name=release.version_name,
        status=release.status,
        readiness_status=readiness_status,
        readiness_percentage=completion_rate,
        total_issues=total,
        resolved_issues=resolved,
        open_blockers_count=len(blockers),
        blocking_issues=blockers
    )
