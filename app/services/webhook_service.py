import re
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import Issue, AuditLog

COMMIT_ISSUE_REGEX = re.compile(
    r"(?:fixes|closes|resolves|fixed|closed|resolved)\s*#(\d+)",
    re.IGNORECASE
)

def process_git_commit_webhook(
    db: Session,
    commit_message: str,
    commit_sha: str = "HEAD",
    author: str = "CI/CD Bot"
) -> Dict[str, Any]:
    matched_ids = [int(m) for m in COMMIT_ISSUE_REGEX.findall(commit_message)]
    unique_ids = list(set(matched_ids))
    
    updated_issues = []

    for issue_id in unique_ids:
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            continue

        old_status = issue.status
        # Transition to QA_VERIFICATION
        issue.status = "QA_VERIFICATION"
        issue.updated_at = datetime.utcnow()

        audit_entry = AuditLog(
            issue_id=issue.id,
            user_id=None,
            action="GIT_WEBHOOK_ADVANCE",
            field_name="status",
            old_value=old_status,
            new_value="QA_VERIFICATION",
            timestamp=datetime.utcnow()
        )
        db.add(audit_entry)
        updated_issues.append(issue.id)

    db.commit()

    return {
        "status": "success",
        "matched_issues": updated_issues,
        "message": f"Processed commit {commit_sha[:8] if commit_sha else 'HEAD'}. Auto-advanced {len(updated_issues)} issue(s) to QA_VERIFICATION."
    }

def process_cicd_pipeline_webhook(
    db: Session,
    pipeline_id: str,
    issue_ids: List[int],
    stage: str,
    build_status: str,
    details: str = ""
) -> Dict[str, Any]:
    """
    Synchronizes build and deployment pipeline status with issue lifecycle.
    """
    advanced_issues = []
    target_status = "RESOLVED" if stage == "DEPLOY" and build_status == "SUCCESS" else "QA_VERIFICATION"

    for issue_id in issue_ids:
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            continue

        old_status = issue.status
        if build_status == "SUCCESS":
            issue.status = target_status
            if target_status == "RESOLVED":
                issue.resolved_at = datetime.utcnow()
        
        issue.updated_at = datetime.utcnow()
        db.add(AuditLog(
            issue_id=issue.id,
            user_id=None,
            action=f"CICD_{stage}_{build_status}",
            field_name="status",
            old_value=old_status,
            new_value=f"{issue.status} (Pipeline #{pipeline_id})",
            timestamp=datetime.utcnow()
        ))
        advanced_issues.append(issue.id)

    db.commit()

    return {
        "status": "success",
        "pipeline_id": pipeline_id,
        "stage": stage,
        "build_status": build_status,
        "affected_issues": advanced_issues,
        "message": f"Pipeline {pipeline_id} ({stage}) {build_status} synchronized with {len(advanced_issues)} issue(s)."
    }