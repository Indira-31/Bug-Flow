from datetime import datetime
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Issue, User, AuditLog

VALID_TRANSITIONS = {
    "REPORTED": ["TRIAGED"],
    "TRIAGED": ["IN_PROGRESS"],
    "IN_PROGRESS": ["CODE_REVIEW"],
    "CODE_REVIEW": ["QA_VERIFICATION", "IN_PROGRESS"],
    "QA_VERIFICATION": ["RESOLVED", "IN_PROGRESS"],
    "RESOLVED": ["CLOSED", "IN_PROGRESS"],  # Supports reopening
    "CLOSED": ["IN_PROGRESS"],              # Supports reopening
}

ROLE_TRANSITION_PERMISSIONS = {
    "ADMIN": ["REPORTED", "TRIAGED", "IN_PROGRESS", "CODE_REVIEW", "QA_VERIFICATION", "RESOLVED", "CLOSED"],
    "DEVELOPER": ["IN_PROGRESS", "CODE_REVIEW", "RESOLVED"],
    "TESTER": ["REPORTED", "QA_VERIFICATION", "CLOSED", "IN_PROGRESS"],
    "TRIAGER": ["TRIAGED", "IN_PROGRESS"],
    "STAKEHOLDER": [],  # Read-only
}

def transition_issue_status(
    db: Session,
    issue: Issue,
    new_status: str,
    current_user: User
) -> Issue:
    old_status = issue.status.upper()
    target_status = new_status.upper()

    if old_status == target_status:
        return issue

    # 1. Check if transition is defined in state machine
    allowed_next_states = VALID_TRANSITIONS.get(old_status, [])
    if target_status not in allowed_next_states:
        # Check invalid shortcut direct jump
        if old_status == "REPORTED" and target_status in ["RESOLVED", "CLOSED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition directly from {old_status} to {target_status} without developer assignment and triage."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid lifecycle transition from {old_status} to {target_status}. Allowed next states: {', '.join(allowed_next_states)}"
        )

    # 2. Check assignee requirement when entering IN_PROGRESS or beyond
    if target_status in ["IN_PROGRESS", "CODE_REVIEW", "RESOLVED"] and not issue.assignee_id:
        if current_user.role in ["DEVELOPER", "ADMIN"]:
            # Auto-claim if developer initiates
            issue.assignee_id = current_user.id
            db.add(AuditLog(
                issue_id=issue.id,
                user_id=current_user.id,
                action="ASSIGNMENT",
                field_name="assignee_id",
                old_value="Unassigned",
                new_value=current_user.full_name,
                timestamp=datetime.utcnow()
            ))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Issue must have an assigned developer before moving to {target_status}."
            )

    # 3. Check role-based permission
    allowed_for_role = ROLE_TRANSITION_PERMISSIONS.get(current_user.role.upper(), [])
    if target_status not in allowed_for_role and current_user.role.upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User role '{current_user.role}' is not authorized to transition issue to '{target_status}'."
        )

    # 4. Handle resolved_at timestamps
    if target_status in ["RESOLVED", "CLOSED"]:
        if not issue.resolved_at:
            issue.resolved_at = datetime.utcnow()
    elif target_status == "IN_PROGRESS" and old_status in ["RESOLVED", "CLOSED"]:
        # Reopening clears resolved_at
        issue.resolved_at = None

    # 5. Apply state change
    issue.status = target_status
    issue.updated_at = datetime.utcnow()

    # 6. Immutable Audit Trail entry
    audit_entry = AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="STATUS_CHANGE",
        field_name="status",
        old_value=old_status,
        new_value=target_status,
        timestamp=datetime.utcnow()
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(issue)
    return issue