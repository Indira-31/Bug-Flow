from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import QualityMetricsResponse, DefectTrendItem, DeveloperWorkloadItem
from app.auth import get_current_user
from app.services.analytics_service import (
    get_quality_metrics,
    get_defect_trends,
    get_plotly_charts_data,
    get_developer_workload_matrix
)

router = APIRouter(prefix="/analytics", tags=["Analytics & Quality Metrics"])

@router.get("/quality-metrics", response_model=QualityMetricsResponse)
def get_metrics_endpoint(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_quality_metrics(db, project_id)

@router.get("/defect-trends", response_model=List[DefectTrendItem])
def get_trends_endpoint(
    project_id: Optional[int] = Query(None),
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_defect_trends(db, project_id, days)

@router.get("/plotly-charts")
def get_plotly_charts_endpoint(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_plotly_charts_data(db, project_id)

@router.get("/developer-workload", response_model=List[DeveloperWorkloadItem])
def get_workload_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_developer_workload_matrix(db)