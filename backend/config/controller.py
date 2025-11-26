from fastapi import APIRouter, HTTPException
from config.schema import Thresholds, ThresholdsResponse, ConfigExample
from config.service import get_thresholds, set_thresholds, clear_thresholds, _load_config_file, _save_config_file
from utils.logger import log_audit

LOG_PATH = "data/logs/audit.log"

router = APIRouter(prefix="/config", tags=["Config"])

# ---------------- Customer APIs ----------------

@router.get("/thresholds", response_model=ThresholdsResponse)
def read_thresholds():
    try:
        low, high, source = get_thresholds()
        log_audit("Thresholds read via API", LOG_PATH)
        return ThresholdsResponse(low=low, high=high, source=source)
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
    except HTTPException as e:
        log_audit(f"HTTPException resetting thresholds: {e.detail}", LOG_PATH)
        raise e
    except Exception as e:
        log_audit(f"Unexpected error resetting thresholds: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Unexpected error resetting thresholds: {str(e)}")

# ---------------- Admin APIs ----------------

@router.get("/admin", response_model=ConfigExample)
def read_full_config():
    try:
        cfg = _load_config_file()
        log_audit("Full config read via Admin API", LOG_PATH)
        return ConfigExample(**cfg)
    except HTTPException as e:
        log_audit(f"HTTPException reading full config: {e.detail}", LOG_PATH)
        raise e
    except Exception as e:
        log_audit(f"Unexpected error reading full config: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Unexpected error reading full config: {str(e)}")

@router.put("/admin", response_model=ConfigExample)
def update_full_config(payload: ConfigExample):
    try:
        cfg = _load_config_file()
        update_data = payload.model_dump(exclude_unset=True)
        cfg.update(update_data)
        _save_config_file(cfg)
        log_audit("Full config updated via Admin API", LOG_PATH)
        return ConfigExample(**cfg)
    except HTTPException as e:
        log_audit(f"HTTPException updating full config: {e.detail}", LOG_PATH)
        raise e
    except Exception as e:
        log_audit(f"Unexpected error updating full config: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Unexpected error updating full config: {str(e)}")
