from typing import Optional
from pydantic import BaseModel

class SeverityDistribution(BaseModel):
    low: int
    medium: int
    high: int

class ActivitySeverityDistribution(BaseModel):
    low: int
    medium: int
    high: int
    none: int

# Uncomment if you later add defects vs time
# from datetime import date
from typing import Dict
# class DefectsOverTimePoint(BaseModel):
#     date: date
#     defects: int

class AnalyticsSummaryResponse(BaseModel):
    total_images: int
    total_defects: int
    total_activities: int
    defect_severity_distribution: SeverityDistribution
    activity_severity_distribution: ActivitySeverityDistribution
    defects_over_time: Dict[str, int]  # commented out for now
    warnings: Optional[list[str]] = None
