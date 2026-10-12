import os
import shutil
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Issue, Comment, Attachment, AuditLog, User
from app.schemas import CommentCreate, CommentResponse, AttachmentResponse, AuditLogResponse
from app.auth import get_current_user

router = APIRouter(prefix="/collaboration", tags=["Collaboration"])

@router.post("/issues/{id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def post_comment(
    id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    new_comment = Comment(
        issue_id=issue.id,
        user_id=current_user.id,
        content=comment_in.content.strip(),
        created_at=datetime.utcnow()
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment

@router.get("/issues/{id}/comments", response_model=List[CommentResponse])
def get_issue_comments(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    return db.query(Comment).filter(Comment.issue_id == id).order_by(Comment.created_at.asc()).all()

@router.post("/issues/{id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_attachment(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Check extension
    allowed_exts = [".png", ".jpg", ".jpeg", ".log", ".txt", ".pdf"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(allowed_exts)}"
        )

    safe_filename = f"issue_{id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_disk_path = settings.UPLOAD_DIR / safe_filename

    with open(file_disk_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_disk_path)

    attachment = Attachment(
        issue_id=issue.id,
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(file_disk_path),
        file_size=file_size,
        content_type=file.content_type or "application/octet-stream",
        created_at=datetime.utcnow()
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment

@router.get("/attachments/{id}/download")
def download_attachment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attachment = db.query(Attachment).filter(Attachment.id == id).first()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    if not os.path.exists(attachment.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File on disk was not found")

    return FileResponse(
        path=attachment.file_path,
        filename=attachment.filename,
        media_type=attachment.content_type
    )

@router.get("/activity-stream", response_model=List[AuditLogResponse])
def get_activity_stream(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()