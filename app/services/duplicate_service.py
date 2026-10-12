import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import Issue

STOPWORDS = {"in", "the", "a", "an", "to", "for", "of", "on", "at", "by", "with", "from", "is", "and", "or"}

def tokenize(text: str) -> set:
    if not text:
        return set()
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = cleaned.split()
    tokens = {w for w in words if w not in STOPWORDS}
    return tokens if tokens else set(words)

def jaccard_similarity(text1: str, text2: str) -> float:
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)

def dice_similarity(text1: str, text2: str) -> float:
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    return (2.0 * len(intersection)) / (len(tokens1) + len(tokens2))

def overlap_similarity(text1: str, text2: str) -> float:
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    return len(intersection) / min(len(tokens1), len(tokens2))

def levenshtein_distance(s1: str, s2: str) -> int:
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def levenshtein_similarity(s1: str, s2: str) -> float:
    max_len = max(len(s1.strip()), len(s2.strip()))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return max(0.0, 1.0 - (dist / max_len))

def calculate_text_similarity(title1: str, title2: str) -> float:
    jaccard = jaccard_similarity(title1, title2)
    dice = dice_similarity(title1, title2)
    overlap = overlap_similarity(title1, title2)
    lev = levenshtein_similarity(title1, title2)
    # Combine token overlap metrics and character distance
    combined = max(jaccard, dice, overlap * 0.85, lev)
    return round(combined, 3)

def check_duplicate_issues(
    db: Session,
    project_id: int,
    new_title: str,
    threshold: float = 0.55
) -> List[Dict[str, Any]]:
    # Compare with existing issues in the same project that are not CLOSED
    issues = db.query(Issue).filter(
        Issue.project_id == project_id,
        Issue.status != "CLOSED"
    ).all()

    matches = []
    for issue in issues:
        similarity = calculate_text_similarity(new_title, issue.title)
        if similarity >= threshold:
            matches.append({
                "id": issue.id,
                "title": issue.title,
                "similarity_score": round(similarity * 100, 1),
                "status": issue.status,
                "severity": issue.severity,
            })

    matches.sort(key=lambda m: -m["similarity_score"])
    return matches