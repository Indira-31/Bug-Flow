from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models import Issue, User

def get_quality_metrics(db: Session, project_id: int = None) -> Dict[str, Any]:
    query = db.query(Issue)
    if project_id:
        query = query.filter(Issue.project_id == project_id)
    
    issues = query.all()
    total_bugs = len(issues)
    if total_bugs == 0:
        return {
            "total_bugs": 0,
            "resolved_bugs": 0,
            "closed_bugs": 0,
            "open_bugs": 0,
            "fix_rate_percentage": 0.0,
            "mean_time_to_resolution_hours": 0.0,
            "defect_leakage_rate_percentage": 0.0,
            "backlog_health_score": 100.0,
        }

    resolved_bugs = sum(1 for i in issues if i.status == "RESOLVED")
    closed_bugs = sum(1 for i in issues if i.status == "CLOSED")
    fixed_count = resolved_bugs + closed_bugs
    open_bugs = total_bugs - fixed_count

    # Fix Rate %
    fix_rate = round((fixed_count / total_bugs) * 100.0, 1)

    # MTTR (Hours)
    resolution_times = [
        (i.resolved_at - i.created_at).total_seconds() / 3600.0
        for i in issues
        if i.resolved_at and i.created_at and i.resolved_at >= i.created_at
    ]
    mttr_hours = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0.0

    # Defect Leakage Rate % (Production bugs / total bugs)
    prod_bugs = sum(
        1 for i in issues
        if (i.dev_stage and i.dev_stage.lower() == "production") or
           (i.environment_details and "prod" in i.environment_details.lower())
    )
    leakage_rate = round((prod_bugs / total_bugs) * 100.0, 1)

    # Backlog Health Score (0 - 100)
    open_critical = sum(1 for i in issues if i.status not in ["RESOLVED", "CLOSED"] and i.severity.upper() == "CRITICAL")
    open_major = sum(1 for i in issues if i.status not in ["RESOLVED", "CLOSED"] and i.severity.upper() == "MAJOR")
    open_minor = sum(1 for i in issues if i.status not in ["RESOLVED", "CLOSED"] and i.severity.upper() == "MINOR")

    score_deduction = (open_critical * 15) + (open_major * 8) + (open_minor * 3)
    health_score = max(0.0, min(100.0, float(100 - score_deduction)))

    return {
        "total_bugs": total_bugs,
        "resolved_bugs": resolved_bugs,
        "closed_bugs": closed_bugs,
        "open_bugs": open_bugs,
        "fix_rate_percentage": fix_rate,
        "mean_time_to_resolution_hours": mttr_hours,
        "defect_leakage_rate_percentage": leakage_rate,
        "backlog_health_score": round(health_score, 1),
    }

def get_defect_trends(db: Session, project_id: int = None, days: int = 14) -> List[Dict[str, Any]]:
    today = datetime.utcnow().date()
    dates = [(today - timedelta(days=d)) for d in reversed(range(days))]

    query = db.query(Issue)
    if project_id:
        query = query.filter(Issue.project_id == project_id)
    all_issues = query.all()

    trends = []
    for d in dates:
        d_str = d.strftime("%Y-%m-%d")
        reported = sum(1 for i in all_issues if i.created_at.date() == d)
        resolved = sum(1 for i in all_issues if i.resolved_at and i.resolved_at.date() == d)
        trends.append({
            "date": d_str,
            "reported": reported,
            "resolved": resolved
        })
    return trends

def get_plotly_charts_data(db: Session, project_id: int = None) -> Dict[str, Any]:
    # 1. Defect Trend (Line chart)
    trends = get_defect_trends(db, project_id, days=14)
    trend_dates = [t["date"] for t in trends]
    reported_counts = [t["reported"] for t in trends]
    resolved_counts = [t["resolved"] for t in trends]

    defect_trend_chart = {
        "data": [
            {
                "x": trend_dates,
                "y": reported_counts,
                "type": "scatter",
                "mode": "lines+markers",
                "name": "New Bugs Reported",
                "line": {"color": "#EF4444", "width": 3},
                "marker": {"size": 6}
            },
            {
                "x": trend_dates,
                "y": resolved_counts,
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Bugs Resolved",
                "line": {"color": "#10B981", "width": 3},
                "marker": {"size": 6}
            }
        ],
        "layout": {
            "title": "14-Day Defect Resolution & Discovery Trend",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "xaxis": {"gridcolor": "#374151", "tickfont": {"color": "#9CA3AF"}},
            "yaxis": {"gridcolor": "#374151", "tickfont": {"color": "#9CA3AF"}, "title": "Number of Issues"},
            "legend": {"font": {"color": "#E5E7EB"}, "orientation": "h", "y": -0.2},
            "font": {"color": "#F3F4F6", "family": "Inter, sans-serif"},
            "margin": {"l": 50, "r": 30, "t": 50, "b": 60}
        }
    }

    # 2. Severity Donut Chart
    query = db.query(Issue)
    if project_id:
        query = query.filter(Issue.project_id == project_id)
    issues = query.all()

    sev_counts = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0}
    for i in issues:
        sev = i.severity.upper()
        if sev in sev_counts:
            sev_counts[sev] += 1
        else:
            sev_counts["MINOR"] += 1

    severity_donut_chart = {
        "data": [
            {
                "values": list(sev_counts.values()),
                "labels": list(sev_counts.keys()),
                "type": "pie",
                "hole": 0.55,
                "marker": {
                    "colors": ["#EF4444", "#F97316", "#EAB308", "#3B82F6"]
                },
                "textinfo": "label+percent",
                "hoverinfo": "label+value+percent"
            }
        ],
        "layout": {
            "title": "Defect Severity Distribution",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#F3F4F6", "family": "Inter, sans-serif"},
            "showlegend": True,
            "legend": {"font": {"color": "#9CA3AF"}},
            "margin": {"l": 20, "r": 20, "t": 50, "b": 20}
        }
    }

    # 3. Workflow Pipeline Bar Chart
    statuses = ["REPORTED", "TRIAGED", "IN_PROGRESS", "CODE_REVIEW", "QA_VERIFICATION", "RESOLVED", "CLOSED"]
    status_counts = {s: 0 for s in statuses}
    for i in issues:
        st = i.status.upper()
        if st in status_counts:
            status_counts[st] += 1

    workflow_bar_chart = {
        "data": [
            {
                "x": statuses,
                "y": [status_counts[s] for s in statuses],
                "type": "bar",
                "marker": {
                    "color": ["#6B7280", "#8B5CF6", "#3B82F6", "#EC4899", "#F59E0B", "#10B981", "#059669"]
                }
            }
        ],
        "layout": {
            "title": "Active Issues by Workflow Stage",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "xaxis": {"gridcolor": "#374151", "tickfont": {"color": "#9CA3AF"}},
            "yaxis": {"gridcolor": "#374151", "tickfont": {"color": "#9CA3AF"}, "title": "Issue Count"},
            "font": {"color": "#F3F4F6", "family": "Inter, sans-serif"},
            "margin": {"l": 50, "r": 30, "t": 50, "b": 70}
        }
    }

    return {
        "defect_trend": defect_trend_chart,
        "severity_donut": severity_donut_chart,
        "workflow_pipeline": workflow_bar_chart
    }

def get_developer_workload_matrix(db: Session) -> List[Dict[str, Any]]:
    devs = db.query(User).filter(
        User.is_active == True,
        User.role.in_(["DEVELOPER", "ADMIN", "TRIAGER"])
    ).all()

    matrix = []
    for dev in devs:
        active_tasks = db.query(Issue).filter(
            Issue.assignee_id == dev.id,
            Issue.status.in_(["IN_PROGRESS", "CODE_REVIEW", "REPORTED", "TRIAGED", "QA_VERIFICATION"])
        ).count()

        completed_issues = db.query(Issue).filter(
            Issue.assignee_id == dev.id,
            Issue.status.in_(["RESOLVED", "CLOSED"])
        ).all()
        completed_fixes = len(completed_issues)

        # Average MTTR for this developer
        res_times = [
            (i.resolved_at - i.created_at).total_seconds() / 3600.0
            for i in completed_issues
            if i.resolved_at and i.created_at and i.resolved_at >= i.created_at
        ]
        avg_mttr = round(sum(res_times) / len(res_times), 1) if res_times else 0.0

        matrix.append({
            "user_id": dev.id,
            "full_name": dev.full_name,
            "username": dev.username,
            "team": dev.team or "Engineering",
            "active_tasks": active_tasks,
            "completed_fixes": completed_fixes,
            "average_mttr_hours": avg_mttr
        })

    matrix.sort(key=lambda m: -m["active_tasks"])
    return matrix