from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import GitWebhookPayload, GitWebhookResponse, CICDPipelineWebhookPayload
from app.services.webhook_service import process_git_commit_webhook, process_cicd_pipeline_webhook

router = APIRouter(prefix="/webhooks", tags=["Webhooks & CI/CD"])

@router.post("/git", response_model=GitWebhookResponse)
def handle_git_webhook(
    payload: GitWebhookPayload,
    db: Session = Depends(get_db)
):
    result = process_git_commit_webhook(
        db=db,
        commit_message=payload.commit_message,
        commit_sha=payload.commit_sha or "HEAD",
        author=payload.author or "CI/CD Bot"
    )
    return GitWebhookResponse(
        status=result["status"],
        matched_issues=result["matched_issues"],
        message=result["message"]
    )

@router.post("/cicd")
def handle_cicd_pipeline_webhook(
    payload: CICDPipelineWebhookPayload,
    db: Session = Depends(get_db)
):
    """
    Module 6: CI/CD integration and automated workflow hooks.
    Synchronizes build and deployment pipelines with issue tracking lifecycle.
    """
    return process_cicd_pipeline_webhook(
        db=db,
        pipeline_id=payload.pipeline_id,
        issue_ids=payload.issue_ids,
        stage=payload.stage.upper(),
        build_status=payload.build_status.upper(),
        details=payload.details or ""
    )