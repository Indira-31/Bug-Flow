import io
import csv
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Issue, Project
from app.services.analytics_service import get_quality_metrics

def generate_issues_csv(db: Session, project_id: Optional[int] = None) -> io.StringIO:
    query = db.query(Issue)
    if project_id:
        query = query.filter(Issue.project_id == project_id)
    issues = query.order_by(Issue.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Bug ID", "Project", "Title", "Severity", "Priority", "Status",
        "Dev Stage", "Affected Modules", "Environment Details",
        "Estimated Effort (pts)", "Priority Score", "Assignee",
        "Reporter", "Created At", "Resolved At"
    ])

    for i in issues:
        writer.writerow([
            f"B-{i.id:03d}",
            i.project.project_name if i.project else "",
            i.title,
            i.severity,
            i.priority,
            i.status,
            i.dev_stage,
            i.affected_modules or "",
            i.environment_details or "",
            i.estimated_effort,
            i.priority_score,
            i.assignee.full_name if i.assignee else "Unassigned",
            i.reporter.full_name if i.reporter else "",
            i.created_at.strftime("%Y-%m-%d %H:%M:%S") if i.created_at else "",
            i.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if i.resolved_at else "N/A"
        ])

    output.seek(0)
    return output

def generate_quality_report_pdf(db: Session, project_id: Optional[int] = None) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    project_name = "All Projects"
    if project_id:
        p = db.query(Project).filter(Project.project_id == project_id).first()
        if p:
            project_name = p.project_name

    metrics = get_quality_metrics(db, project_id)
    
    query = db.query(Issue)
    if project_id:
        query = query.filter(Issue.project_id == project_id)
    recent_critical = query.filter(Issue.severity.in_(["CRITICAL", "MAJOR"])).order_by(Issue.id.desc()).limit(8).all()

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")

        # Header Title
        ax.text(0.05, 0.95, "BugFlow Platform - Executive Quality & Defect Report", fontsize=16, weight="bold", color="#1E293B")
        ax.text(0.05, 0.92, f"Project: {project_name} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", fontsize=10, color="#64748B")
        ax.plot([0.05, 0.95], [0.90, 0.90], color="#2563EB", lw=2)

        # KPI Summary Table
        ax.text(0.05, 0.86, "1. Executive Quality Scorecard", fontsize=12, weight="bold", color="#0F172A")
        kpi_data = [
            ["Metric", "Value", "Target Benchmark", "Status"],
            ["Total Defects Tracked", str(metrics["total_bugs"]), "N/A", "Monitored"],
            ["Bug Fix Rate (%)", f"{metrics['fix_rate_percentage']}%", ">= 80.0%", "Optimal" if metrics["fix_rate_percentage"] >= 80 else "Attention"],
            ["Mean Time to Resolution (MTTR)", f"{metrics['mean_time_to_resolution_hours']} hrs", "< 48.0 hrs", "Healthy" if metrics["mean_time_to_resolution_hours"] <= 48 else "Moderate"],
            ["Backlog Health Score", f"{metrics['backlog_health_score']} / 100", ">= 85.0", "Pass" if metrics["backlog_health_score"] >= 85 else "Caution"],
            ["Defect Leakage Rate (%)", f"{metrics['defect_leakage_rate_percentage']}%", "< 10.0%", "Controlled" if metrics["defect_leakage_rate_percentage"] <= 10 else "High"],
        ]
        table_kpi = ax.table(cellText=kpi_data, loc="upper left", bbox=[0.05, 0.62, 0.90, 0.22])
        table_kpi.auto_set_font_size(False)
        table_kpi.set_fontsize(8.5)
        for (r, c), cell in table_kpi.get_celld().items():
            if r == 0:
                cell.set_facecolor("#2563EB")
                cell.set_text_props(color="white", weight="bold")
            else:
                cell.set_facecolor("#F8FAFC" if r % 2 == 0 else "white")

        # Critical Defects Table
        ax.text(0.05, 0.56, "2. High-Severity & Critical Issues Registry", fontsize=12, weight="bold", color="#0F172A")
        crit_rows = [["ID", "Title", "Severity", "Priority", "Status", "Assignee"]]
        for c_iss in recent_critical:
            assignee_name = c_iss.assignee.full_name if c_iss.assignee else "Unassigned"
            title_trunc = (c_iss.title[:32] + "...") if len(c_iss.title) > 32 else c_iss.title
            crit_rows.append([
                f"B-{c_iss.id:03d}",
                title_trunc,
                c_iss.severity,
                c_iss.priority,
                c_iss.status,
                assignee_name
            ])
        if len(crit_rows) == 1:
            crit_rows.append(["None", "No open critical or major defects registered", "-", "-", "-", "-"])

        table_crit = ax.table(cellText=crit_rows, loc="upper left", bbox=[0.05, 0.20, 0.90, 0.33])
        table_crit.auto_set_font_size(False)
        table_crit.set_fontsize(8)
        for (r, c), cell in table_crit.get_celld().items():
            if r == 0:
                cell.set_facecolor("#DC2626")
                cell.set_text_props(color="white", weight="bold")
            else:
                cell.set_facecolor("#FEF2F2" if r % 2 == 0 else "white")

        # Footer Notice
        ax.plot([0.05, 0.95], [0.12, 0.12], color="#CBD5E1", lw=1)
        ax.text(0.05, 0.08, "BugFlow Platform Quality Assurance System | Compliant with ISO/IEC 25010 Software Quality Standards", fontsize=7.5, color="#94A3B8")
        ax.text(0.05, 0.05, "This document contains automated real-time defect telemetry. Confidential - Internal Use Only.", fontsize=7.5, color="#94A3B8")

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    buf.seek(0)
    return buf.getvalue()