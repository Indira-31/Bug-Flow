from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.export_service import generate_issues_csv, generate_quality_report_pdf

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/csv")
def export_csv(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    stream = generate_issues_csv(db, project_id)
    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bugflow_defects_registry.csv"}
    )

@router.get("/pdf")
def export_pdf(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    pdf_bytes = generate_quality_report_pdf(db, project_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=bugflow_quality_scorecard.pdf"}
    )