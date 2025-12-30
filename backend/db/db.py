from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, func
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

# Base class for models
Base = declarative_base()

class Activity(Base):
    __tablename__ = "activities"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | in-progress | completed | error
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    from_value = Column(String, nullable=True)
    to_value = Column(String, nullable=True)

    images = relationship("ActivityImage", back_populates="activity", cascade="all, delete-orphan")

class ActivityImage(Base):
    __tablename__ = "activity_images"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(String, ForeignKey("activities.id"), nullable=False)
    filename = Column(String, nullable=False)  # e.g., "patches.png"
    status = Column(String, default="pending")  # pending | processing | no_defects | defects_detected | error
    detections = Column(JSON)

    # Defect counts
    high_defects = Column(Integer, default=0)
    medium_defects = Column(Integer, default=0)
    low_defects = Column(Integer, default=0)

    # Blob URLs
    original_blob_url = Column(String)     # https://.../images/original/<filename>
    annotated_blob_url = Column(String)    # https://.../images/annotated/<filename>

    # Add created_at for reliable sorting
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    activity = relationship("Activity", back_populates="images")