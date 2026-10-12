from typing import Tuple

SEVERITY_WEIGHTS = {
    "CRITICAL": 4,
    "MAJOR": 3,
    "MINOR": 2,
    "TRIVIAL": 1,
}

URGENCY_WEIGHTS = {
    "HIGH URGENCY": 3,
    "MEDIUM URGENCY": 2,
    "LOW URGENCY": 1,
}

# Category name keyword fallbacks if urgency text needs inference
CATEGORY_URGENCY_MAP = {
    "security vulnerability": 3,
    "database error": 3,
    "api gateway": 2,
    "backend logic": 2,
    "ui glitch": 1,
}

def get_severity_weight(severity: str) -> int:
    return SEVERITY_WEIGHTS.get(severity.strip().upper(), 2)

def get_urgency_weight(urgency_str: str, category_name: str = "") -> int:
    clean_urg = urgency_str.strip().upper()
    if clean_urg in URGENCY_WEIGHTS:
        return URGENCY_WEIGHTS[clean_urg]
    
    clean_cat = category_name.strip().lower()
    for cat_key, weight in CATEGORY_URGENCY_MAP.items():
        if cat_key in clean_cat:
            return weight
            
    if "high" in clean_urg:
        return 3
    elif "low" in clean_urg:
        return 1
    return 2

def calculate_priority(severity: str, urgency_str: str, category_name: str = "") -> Tuple[float, str, int, int]:
    """
    Priority Score = Severity Weight * Category Urgency Weight
    Score >= 10 -> URGENT
    Score 7 - 9 -> HIGH
    Score 4 - 6 -> MEDIUM
    Score < 4  -> LOW
    """
    sev_weight = get_severity_weight(severity)
    urg_weight = get_urgency_weight(urgency_str, category_name)
    score = float(sev_weight * urg_weight)

    if score >= 10:
        priority = "URGENT"
    elif score >= 7:
        priority = "HIGH"
    elif score >= 4:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    return score, priority, sev_weight, urg_weight