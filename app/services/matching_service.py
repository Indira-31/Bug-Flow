import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import User, Issue

def extract_keywords(text: str) -> set:
    if not text:
        return set()
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = set(cleaned.split())
    # expand synonyms
    synonyms = {
        "db": {"database", "sql", "postgres", "postgresql", "sqlite"},
        "database": {"sql", "postgres", "postgresql", "db", "query"},
        "sql": {"database", "postgres", "postgresql", "db"},
        "auth": {"login", "jwt", "security", "token", "password", "oauth"},
        "login": {"auth", "jwt", "security", "token", "password"},
        "security": {"vulnerability", "auth", "jwt", "owasp", "token"},
        "frontend": {"react", "css", "html", "javascript", "ui", "tailwind"},
        "ui": {"frontend", "react", "css", "html", "javascript", "view"},
        "api": {"rest", "fastapi", "gateway", "endpoint", "http"},
        "backend": {"python", "fastapi", "api", "sqlalchemy", "server"},
    }
    expanded = set(words)
    for word in words:
        if word in synonyms:
            expanded.update(synonyms[word])
    return expanded

def match_developers_for_bug(
    db: Session,
    title: str,
    description: str = "",
    affected_modules: str = "",
    limit: int = 3
) -> List[Dict[str, Any]]:
    # Get all active developers
    developers = db.query(User).filter(
        User.is_active == True,
        User.role.in_(["DEVELOPER", "ADMIN", "TRIAGER"])
    ).all()

    bug_text = f"{title} {description} {affected_modules}"
    bug_keywords = extract_keywords(bug_text)

    scored_devs = []

    for dev in developers:
        # Check active workload (bugs in progress or review)
        active_tasks = db.query(Issue).filter(
            Issue.assignee_id == dev.id,
            Issue.status.in_(["IN_PROGRESS", "CODE_REVIEW", "REPORTED", "TRIAGED"])
        ).count()

        # Skill matching
        dev_skills_set = extract_keywords(dev.core_skills or "")
        team_set = extract_keywords(dev.team or "")
        all_dev_keywords = dev_skills_set.union(team_set)

        matched_skills = bug_keywords.intersection(all_dev_keywords)
        match_count = len(matched_skills)

        # Baseline score: if proficiency is high or skills exist
        proficiency_boost = 10 if dev.proficiency in ["Senior", "Lead"] else 5
        
        if match_count > 0:
            raw_score = 65.0 + min(match_count * 12.0, 28.0) + proficiency_boost
        else:
            raw_score = 45.0 + proficiency_boost

        # Workload penalty (reduce score if overloaded)
        workload_penalty = active_tasks * 6.0
        final_score = max(20.0, min(98.0, raw_score - workload_penalty))

        # Generate human-readable rationale
        skill_highlight = ", ".join(list(matched_skills)[:2]) if matched_skills else dev.proficiency or "Core"
        rationale = f"{skill_highlight.capitalize()} specialist, {active_tasks} active task(s)"

        scored_devs.append({
            "user_id": dev.id,
            "full_name": dev.full_name,
            "username": dev.username,
            "team": dev.team or "Engineering",
            "core_skills": dev.core_skills or "General",
            "active_tasks": active_tasks,
            "match_percentage": round(final_score, 1),
            "rationale": rationale,
        })

    # Sort descending by match percentage, then ascending by active tasks
    scored_devs.sort(key=lambda d: (-d["match_percentage"], d["active_tasks"]))
    return scored_devs[:limit]