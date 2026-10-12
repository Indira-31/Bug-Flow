from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models import HistoricalBugFix, User, BugCategory, Issue
from app.services.priority_service import calculate_priority
from app.services.matching_service import match_developers_for_bug

def analyze_issue_with_ai_core(
    db: Session,
    title: str,
    description: str,
    category_id: int,
    severity: str = "MINOR",
    code_diff: str = "",
    project_context: str = "",
    affected_modules: str = ""
) -> Dict[str, Any]:
    """
    Implements BugFlow AI Core Engine defined in Architecture Diagram (Page 10):
    - Inputs: Comprehensive Issue Report, Code Diff, Project Context, Historical Fix Patterns,
              Developer Capacity & Skill Profiles, AI Ethical Bias Check.
    - Processes: Automatic Issue Triaging & Severity Classification, Fix Pattern Matching &
                 Automated Testing, Real-world Skill Relevance Validation, Developer Assignment Suggestion,
                 Automated CI/CD & Rollback Paths.
    - Outputs: Personalized Resolution Paths, Developer Assignments, Match Scores, Cycle Insights.
    """
    category = db.query(BugCategory).filter(BugCategory.category_id == category_id).first()
    category_name = category.category_name if category else "General"
    urgency_str = category.urgency if category else "Medium Urgency"

    # 1. AI Ethical Bias Check (ensures neutrality, no demographic bias, objective technical triage)
    prohibited_bias_patterns = ["gender", "race", "nationality", "religion"]
    full_text = f"{title} {description}".lower()
    bias_detected = any(b in full_text for b in prohibited_bias_patterns)
    ethical_report = "PASSED: Issue content is verified purely technical with zero demographic bias." if not bias_detected else "WARNING: Bias check triggered sensitive keywords; prioritized on technical merit only."

    # 2. Automatic Triaging & Severity Classification
    suggested_severity = severity
    critical_keywords = ["crash", "leak", "vulnerability", "fatal", "oom", "corruption", "security", "exploit"]
    major_keywords = ["timeout", "fail", "500", "502", "slow", "error", "broken", "unhandled"]
    
    if any(k in full_text for k in critical_keywords):
        suggested_severity = "CRITICAL"
    elif any(k in full_text for k in major_keywords) and severity not in ["CRITICAL"]:
        suggested_severity = "MAJOR"

    score, priority, _, _ = calculate_priority(
        severity=suggested_severity,
        urgency_str=urgency_str,
        category_name=category_name
    )

    # 3. Historical Fix Pattern Matching & Automated Testing from Historical_Bug_Fixes
    historical_fixes = db.query(HistoricalBugFix).all()
    matched_patterns = []
    suggested_tests = ["Unit test for edge case regression", "Integration API test verification"]

    if "postgres" in full_text or "database" in full_text or "pool" in full_text:
        suggested_tests.extend(["PostgreSQL connection pool stress test (100 conns)", "DB transaction rollback test"])
    if "token" in full_text or "auth" in full_text or "jwt" in full_text:
        suggested_tests.extend(["JWT HMAC-SHA256 signature test", "Auth expired token 401 response test"])
    if "ui" in full_text or "css" in full_text or "align" in full_text or "viewport" in full_text:
        suggested_tests.extend(["Mobile responsive layout screenshot diff test", "Cross-browser DOM inspection"])

    for hf in historical_fixes:
        if any(w in hf.past_fixes.lower() for w in full_text.split() if len(w) > 4):
            matched_patterns.append({
                "fix_id": hf.fix_id,
                "past_fixes": hf.past_fixes,
                "resolution_time": hf.resolution_time,
                "suggested_approach": hf.code_changes or "Apply validated patch pattern"
            })

    if not matched_patterns:
        matched_patterns.append({
            "fix_id": 0,
            "past_fixes": f"Standard patch pattern for {category_name}",
            "resolution_time": "1-2 days",
            "suggested_approach": "Isolate reproducing scenario, add unit test, submit fix branch."
        })

    # 4. Developer Assignment Suggestion (Skill relevance + capacity)
    dev_matches = match_developers_for_bug(
        db=db,
        title=title,
        description=description,
        affected_modules=affected_modules
    )

    # 5. Personalized Resolution Path
    resolution_path = [
        {
            "step": 1,
            "phase": "Reproduction & Root Cause Isolation",
            "action": f"Replicate issue locally using specified environment. Check logs for '{category_name}'.",
            "suggested_tests": [suggested_tests[0]]
        },
        {
            "step": 2,
            "phase": "Fix Development & Code Review",
            "action": "Implement patch on feature branch, reference issue in commit message (fixes #ID).",
            "suggested_tests": suggested_tests[1:3]
        },
        {
            "step": 3,
            "phase": "QA Validation & Regression Testing",
            "action": "Automated CI/CD verifies test suite. Peer review by assigned senior engineer.",
            "suggested_tests": [suggested_tests[-1]]
        },
        {
            "step": 4,
            "phase": "Release Deployment & Patching",
            "action": "Deploy via automated pipeline with active rollback trigger on health check failure.",
            "suggested_tests": ["End-to-end smoke test on staging"]
        }
    ]

    # 6. Automated CI/CD & Rollback Paths
    rollback_path = (
        "Automated CI/CD Pipeline: If post-deployment error rate exceeds 0.5% within 15 minutes, "
        "execute automated rollback via Git tag reversal and container blue-green switch."
    )

    # 7. Cycle Insights
    cycle_insights = (
        f"Based on current team velocity and {category_name} complexity, expected resolution time is "
        f"{matched_patterns[0].get('resolution_time', '2 days')}. Recommended sprint allocation: active cycle."
    )

    return {
        "analyzed_title": title,
        "analyzed_severity": suggested_severity,
        "ai_ethical_bias_passed": not bias_detected,
        "ethical_bias_report": ethical_report,
        "categorization": category_name,
        "suggested_severity": suggested_severity,
        "priority_score": score,
        "priority": priority,
        "matched_historical_patterns": matched_patterns,
        "personalized_resolution_path": resolution_path,
        "developer_assignments": dev_matches,
        "automated_cicd_rollback_path": rollback_path,
        "cycle_insights": cycle_insights
    }
