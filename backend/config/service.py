import json
import os
from fastapi import HTTPException
from typing import Tuple
from config.schema import Thresholds
from utils.logger import log_audit
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"
LOG_PATH = "data/logs/audit.log"

DEFAULT_LOW = 0.3
DEFAULT_HIGH = 0.7

def _load_config_file() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {
            "low": DEFAULT_LOW,
            "high": DEFAULT_HIGH
        }
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        log_audit(f"Error loading config.json: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail="Failed to load config.json")

def _save_config_file(data: dict):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_audit(f"Error saving config.json: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail="Failed to save config.json")

def get_thresholds() -> Tuple[float, float, str]:
    try:
        cfg = _load_config_file()
        low = cfg.get("low", DEFAULT_LOW)
        high = cfg.get("high", DEFAULT_HIGH)
        source = "user" if os.path.exists(CONFIG_FILE) else "default"
        log_audit(f"Thresholds retrieved: low={low}, high={high}, source={source}", LOG_PATH)
        return low, high, source
    except HTTPException as e:
        raise e
    except Exception as e:
        log_audit(f"Unexpected error retrieving thresholds: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Unexpected error retrieving thresholds: {str(e)}")

def set_thresholds(new: Thresholds) -> Tuple[float, float]:
    try:
        cfg = _load_config_file()
        # Preserve other keys (Azure/IoT credentials) instead of overwriting
        cfg["low"] = new.low
        cfg["high"] = new.high
        _save_config_file(cfg)
        log_audit(f"Thresholds updated: low={new.low}, high={new.high}", LOG_PATH)
        return new.low, new.high
    except HTTPException as e:
        raise e
    except Exception as e:
        log_audit(f"Unexpected error setting thresholds: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Unexpected error setting thresholds: {str(e)}")

def clear_thresholds():
    try:
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        log_audit("Thresholds reset to defaults", LOG_PATH)
    except Exception as e:
        log_audit(f"Error resetting thresholds: {str(e)}", LOG_PATH)
        raise HTTPException(status_code=500, detail=f"Failed to reset thresholds: {str(e)}")

