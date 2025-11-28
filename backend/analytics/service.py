from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import Counter

from db import Activity, ActivityImage
from config.service import get_thresholds
from utils.logger import log_audit

LOG_PATH = "data/logs/audit.log"

from datetime import date, timedelta
from calendar import monthrange

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _compute_image_counts(
        detections: Optional[List[Dict]], low_thr: float, high_thr: float
    ) -> Tuple[int, int, int]:
        """Compute low/medium/high defect counts dynamically from detections JSON."""
        if not detections:
            return 0, 0, 0

        low = medium = high = 0
        for det in detections:
            conf = float(det.get("confidence", 0.0))
            if conf >= high_thr:
                high += 1
            elif conf >= low_thr:
                medium += 1
            else:
                low += 1
        return low, medium, high

    def get_summary(
        self, override_low: Optional[float] = None, override_high: Optional[float] = None
    ) -> Dict:
        try:
            warnings: List[str] = []

            cfg_low, cfg_high, src = get_thresholds()
            low_thr = override_low if override_low is not None else cfg_low
            high_thr = override_high if override_high is not None else cfg_high

            # Totals
            total_activities = self.db.query(func.count(Activity.id)).scalar() or 0
            total_images = self.db.query(func.count(ActivityImage.id)).scalar() or 0

            # Fetch detections + created_at
            all_images = self.db.query(
                ActivityImage.activity_id,
                ActivityImage.detections,
                ActivityImage.created_at
            ).all()

            total_low = total_medium = total_high = 0
            activity_map: Dict[str, Dict[str, int]] = {}

            # defects vs time counters
            defects_by_day = Counter()
            defects_by_month = Counter()      # CHANGE: added monthly aggregation
            defects_by_weekday = Counter()    # CHANGE: added weekday aggregation

            for act_id, detections, created_at in all_images:
                img_low, img_med, img_high = self._compute_image_counts(
                    detections, low_thr, high_thr
                )
                total_low += img_low
                total_medium += img_med
                total_high += img_high

                if act_id not in activity_map:
                    activity_map[act_id] = {"low": 0, "medium": 0, "high": 0}
                activity_map[act_id]["low"] += img_low
                activity_map[act_id]["medium"] += img_med
                activity_map[act_id]["high"] += img_high

                # aggregate defects by day/month/weekday
                if created_at:
                    day = created_at.date().isoformat()
                    defects_by_day[day] += (img_low + img_med + img_high)

                    month = created_at.strftime("%Y-%m")       # e.g. "2025-11"
                    defects_by_month[month] += (img_low + img_med + img_high)

                    weekday = created_at.strftime("%A")        # e.g. "Monday"
                    defects_by_weekday[weekday] += (img_low + img_med + img_high)

            total_defects = total_low + total_medium + total_high

            defect_severity_distribution = {
                "low": total_low,
                "medium": total_medium,
                "high": total_high,
            }

            # Classify activities
            act_low = act_medium = act_high = act_none = 0
            activities_with_images = set(activity_map.keys())

            for counts in activity_map.values():
                l, m, h = counts["low"], counts["medium"], counts["high"]
                if l == 0 and m == 0 and h == 0:
                    act_none += 1
                elif h > 0:
                    act_high += 1
                elif m > 0:
                    act_medium += 1
                else:
                    act_low += 1

            # Activities with no images
            activities_without_images = (
                self.db.query(func.count(Activity.id))
                .filter(~Activity.id.in_(activities_with_images) if activities_with_images else True)
                .scalar()
                or 0
            )
            if activities_without_images > 0:
                warnings.append(
                    f"{activities_without_images} activities have no images; counted as 'none'."
                )
                act_none += activities_without_images

            activity_severity_distribution = {
                "low": act_low,
                "medium": act_medium,
                "high": act_high,
                "none": act_none,
            }

            if src == "default":
                warnings.append("Using default thresholds; update /config/thresholds to customize.")

            result = {
                "total_images": total_images,
                "total_defects": total_defects,
                "total_activities": total_activities,
                "defect_severity_distribution": defect_severity_distribution,
                "activity_severity_distribution": activity_severity_distribution,
                "defects_over_time": dict(defects_by_day),        # daily trend
                "defects_by_month": dict(defects_by_month),       # CHANGE: monthly trend
                "defects_by_weekday": dict(defects_by_weekday),   # CHANGE: weekday trend
                "warnings": warnings or None,
            }

            log_audit("Analytics summary computed successfully", LOG_PATH)
            return result

        except Exception as e:
            log_audit(f"Error computing analytics summary: {str(e)}", LOG_PATH)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to compute analytics summary: {str(e)}"
            )
        
    def get_monthly_defects(
        self, year: Optional[int] = None, month: Optional[int] = None,
        override_low: Optional[float] = None, override_high: Optional[float] = None
    ) -> Dict:
        """
        Return daily defect counts for a given month (defaults to current month).
        """
        try:
            today = date.today()
            year = year or today.year
            month = month or today.month

            cfg_low, cfg_high, _ = get_thresholds()
            low_thr = override_low if override_low is not None else cfg_low
            high_thr = override_high if override_high is not None else cfg_high

            # Get all images created in this month
            start_date = date(year, month, 1)
            end_day = monthrange(year, month)[1]
            end_date = date(year, month, end_day)

            all_images = self.db.query(
                ActivityImage.detections,
                ActivityImage.created_at
            ).filter(
                ActivityImage.created_at >= start_date,
                ActivityImage.created_at <= end_date
            ).all()

            # Initialize daily counts
            month_usage: List[Dict] = []
            for day in range(1, end_day + 1):
                period = date(year, month, day).isoformat()
                month_usage.append({"period": period, "defect_count": 0})

            # Fill counts
            for detections, created_at in all_images:
                if not created_at:
                    continue
                day_index = created_at.day - 1
                img_low, img_med, img_high = self._compute_image_counts(
                    detections, low_thr, high_thr
                )
                month_usage[day_index]["defect_count"] += (img_low + img_med + img_high)

            result = {"month_usage": month_usage}
            log_audit(f"Monthly defects computed for {year}-{month}", LOG_PATH)
            return result

        except Exception as e:
            log_audit(f"Error computing monthly defects: {str(e)}", LOG_PATH)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to compute monthly defects: {str(e)}"
            )
