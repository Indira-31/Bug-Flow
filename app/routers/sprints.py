from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Sprint, Issue, Project, User, AuditLog
from app.schemas import SprintCreate, SprintResponse, IssueResponse
from app.auth import get_current_user, require_roles

router = APIRouter(prefix="/sprints", tags=["Sprints"])

@router.post("/", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
def create_sprint(
    sprint_in: SprintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TRIAGER", "DEVELOPER"]))
):
    project = db.query(Project).filter(Project.project_id == sprint_in.project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    new_sprint = Sprint(
        project_id=sprint_in.project_id,
        sprint_name=sprint_in.sprint_name.strip(),
        goal=sprint_in.goal,
        start_date=sprint_in.start_date,
        end_date=sprint_in.end_date,
        status=sprint_in.status.upper(),
        velocity=0.0,
        created_at=datetime.utcnow()
    )
    db.add(new_sprint)
    db.commit()
    db.refresh(new_sprint)
    new_sprint.issue_count = 0
    new_sprint.resolved_count = 0
    return new_sprint

@router.get("/", response_model=List[SprintResponse])
def list_sprints(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Sprint)
    if project_id:
        query = query.filter(Sprint.project_id == project_id)
    sprints = query.order_by(Sprint.sprint_id.desc()).all()

    for s in sprints:
        issues = db.query(Issue).filter(Issue.sprint_id == s.sprint_id).all()
        s.issue_count = len(issues)
        s.resolved_count = sum(1 for i in issues if i.status in ["RESOLVED", "CLOSED"])

    return sprints

@router.get("/backlog", response_model=List[IssueResponse])
def get_backlog_issues(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Issue).filter(Issue.sprint_id == None)
    if project_id:
        query = query.filter(Issue.project_id == project_id)
    return query.order_by(Issue.created_at.desc()).all()

@router.post("/{id}/add-issue/{issue_id}", response_model=IssueResponse)
def add_issue_to_sprint(
    id: int,
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TRIAGER", "DEVELOPER"]))
):
    sprint = db.query(Sprint).filter(Sprint.sprint_id == id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sprint not found")

    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    old_sprint_name = issue.sprint.sprint_name if issue.sprint else "Product Backlog"
    issue.sprint_id = sprint.sprint_id
    issue.updated_at = datetime.utcnow()

    # Immutable Audit Log
    db.add(AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="SPRINT_ASSIGN",
        field_name="sprint_id",
        old_value=old_sprint_name,
        new_value=sprint.sprint_name,
        timestamp=datetime.utcnow()
    ))
    db.commit()
    db.refresh(issue)
    return issue

@router.patch("/{id}/status", response_model=SprintResponse)
def update_sprint_status(
    id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TRIAGER"]))
):
    sprint = db.query(Sprint).filter(Sprint.sprint_id == id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sprint not found")

    sprint.status = new_status.upper()
    issues = db.query(Issue).filter(Issue.sprint_id == sprint.sprint_id).all()
    resolved_count = sum(1 for i in issues if i.status in ["RESOLVED", "CLOSED"])
    
    # Velocity tracker: calculate velocity (resolved issues count / total story points resolved)
    if sprint.status == "COMPLETED":
        sprint.velocity = float(resolved_count)

    db.commit()
    db.refresh(sprint)
    sprint.issue_count = len(issues)
    sprint.resolved_count = resolved_count
    return sprint