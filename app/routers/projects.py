from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, BugCategory, Issue, User
from app.schemas import ProjectCreate, ProjectResponse, BugCategoryResponse
from app.auth import get_current_user, require_roles

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "TRIAGER"]))
):
    existing = db.query(Project).filter(Project.project_name == project_in.project_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{project_in.project_name}' already exists"
        )
    project = Project(
        project_name=project_in.project_name,
        codebase=project_in.codebase,
        development_cycle=project_in.development_cycle
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    project.issue_count = 0
    return project

@router.get("/", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    projects = db.query(Project).order_by(Project.project_id.asc()).all()
    for p in projects:
        p.issue_count = db.query(Issue).filter(Issue.project_id == p.project_id).count()
    return projects

@router.get("/categories", response_model=List[BugCategoryResponse])
def list_bug_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(BugCategory).order_by(BugCategory.category_id.asc()).all()