from pydantic import BaseModel, Field, model_validator
from typing import Optional

class Thresholds(BaseModel):
    low: float = Field(..., gt=0.0, lt=1.0, description="Low threshold (0-1, exclusive)")
    high: float = Field(..., gt=0.0, lt=1.0, description="High threshold (0-1, exclusive)")

    @model_validator(mode="after")
    def validate_order(self) -> "Thresholds":
        if not (self.low < self.high):
            raise ValueError("low must be strictly less than high")
        return self

class ThresholdsResponse(BaseModel):
    low: float
    high: float
    source: str  # "user" or "default"

class ConfigExample(BaseModel):
    low: float
    high: float
    AZURE_ACCOUNT_NAME: Optional[str] = None
    AZURE_ACCOUNT_KEY: Optional[str] = None
    BLOB_CONTAINER_NAME: Optional[str] = None
    IOT_DEVICE_ID: Optional[str] = None
    IOT_DEVICE_ENDPOINT: Optional[str] = None
    IOT_API_KEY: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "low": 0.3,
                "high": 0.7,
                "AZURE_ACCOUNT_NAME": "dummy_account",
                "AZURE_ACCOUNT_KEY": "dummy_key",
                "BLOB_CONTAINER_NAME": "dummy_container",
                "IOT_DEVICE_ID": "dummy_device",
                "IOT_DEVICE_ENDPOINT": "http://dummy.iot/device/images",
                "IOT_API_KEY": "dummy_key"
            }
        }
