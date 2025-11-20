from pydantic import BaseModel, Field, model_validator

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
