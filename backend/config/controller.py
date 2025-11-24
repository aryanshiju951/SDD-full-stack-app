from fastapi import APIRouter, HTTPException
from config.schema import Thresholds, ThresholdsResponse
from config.service import get_thresholds, set_thresholds, clear_thresholds
from utils.logger import log_audit

LOG_PATH = "data/logs/audit.log"

router = APIRouter(prefix="/config", tags=["Config"])

@router.get("/thresholds", response_model=ThresholdsResponse)
def read_thresholds():
    try:
        low, high, source = get_thresholds()
        log_audit("Thresholds read via API", LOG_PATH)
        return ThresholdsResponse(low=low, high=high, source=source)
        # No changes here credentials are not exposed in API
    except HTTPException as e:
        log_audit(f"HTTPException reading thresholds: {e.detail}", LOG_PATH)
        raise e
    except Exception as e:
        log_audit(f"Unexpected error reading thresholds: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Unexpected error reading thresholds: {str(e)}")

@router.put("/thresholds", response_model=ThresholdsResponse)
def update_thresholds(payload: Thresholds):
    try:
        low, high = set_thresholds(payload)
        log_audit("Thresholds updated via API", LOG_PATH)
        return ThresholdsResponse(low=low, high=high, source="user")
        # No changes here — credentials remain hidden
    except HTTPException as e:
        log_audit(f"HTTPException updating thresholds: {e.detail}", LOG_PATH)
        raise e
    except Exception as e:
        log_audit(f"Unexpected error updating thresholds: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Unexpected error updating thresholds: {str(e)}")

@router.delete("/thresholds", response_model=ThresholdsResponse)
def reset_thresholds():
    try:
        clear_thresholds()
        low, high, source = get_thresholds()
        log_audit("Thresholds reset via API", LOG_PATH)
        return ThresholdsResponse(low=low, high=high, source=source)
        # No changes here — credentials remain hidden
    except HTTPException as e:
        log_audit(f"HTTPException resetting thresholds: {e.detail}", LOG_PATH)
        raise e
    except Exception as e:
        log_audit(f"Unexpected error resetting thresholds: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Unexpected error resetting thresholds: {str(e)}")
