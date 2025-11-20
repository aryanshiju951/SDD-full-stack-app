from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from analytics.schema import AnalyticsSummaryResponse
from analytics.service import AnalyticsService
from db import get_db
from utils.logger import log_audit

LOG_PATH = "data/logs/audit.log"

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    db: Session = Depends(get_db),
    low_threshold: float = Query(None, gt=0.0, lt=1.0, description="Override low threshold (0-1, exclusive)"),
    high_threshold: float = Query(None, gt=0.0, lt=1.0, description="Override high threshold (0-1, exclusive)"),
):
    """
    Dashboard analytics:
      - total_images
      - total_defects
      - total_activities
      - defect_severity_distribution (low/medium/high)
      - activity_severity_distribution (low/medium/high)
    Thresholds are loaded from config but can be overridden per request.
    """
    try:
        if low_threshold is not None and high_threshold is not None and not (low_threshold < high_threshold):
            raise HTTPException(status_code=400, detail="low_threshold must be strictly less than high_threshold")

        service = AnalyticsService(db)
        summary = service.get_summary(override_low=low_threshold, override_high=high_threshold)
        log_audit("Analytics summary endpoint called successfully", LOG_PATH)
        return summary

    except HTTPException as e:
        log_audit(f"HTTPException in analytics summary: {e.detail}", LOG_PATH)
        raise e
    except Exception as e:
        log_audit(f"Unexpected error in analytics summary: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
