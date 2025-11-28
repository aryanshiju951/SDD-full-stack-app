from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ActivityCreate(BaseModel):
    name: str

class ImageResponse(BaseModel):
    id: int
    filename: str
    status: str
    original_blob_url: Optional[str]
    annotated_blob_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True   # ensures compatibility with SQLAlchemy models

class ActivityResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime
    from_value: Optional[str]
    to_value:Optional[str]
    images: List[ImageResponse]

    class Config:
        from_attributes = True

class SyncResponse(BaseModel):
    message: str
    activity_status: str
    new_images_found: int
    processed_images: int
    error_images: int

class DefectImageSummary(BaseModel):
    filename: str
    original_blob_url: Optional[str]
    annotated_blob_url: Optional[str]
    detections: List[Dict[str, Any]]

class SummaryResponse(BaseModel):
    activity_id: str
    high_defects: int
    medium_defects: int
    low_defects: int
    defect_images: List[DefectImageSummary]
    activity_status: str

class DeleteResponse(BaseModel):
    message: str
    activity_id: str

# Response model for sync_images_demo
class SyncImagesResponse(BaseModel):
    message: str
    activity_status: str
    images: List[Dict[str, str]]   
    summary: Dict[str, Any]  

# New one
class DetectionBBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class Detection(BaseModel):
    id: int
    class_: str = Field(..., alias="class")
    confidence: float
    bbox: DetectionBBox

    model_config = {
        "populate_by_name": True
    }
    
class ImageDetections(BaseModel):
    image_id: int
    filename: str
    detections: List[Detection]

class AnnotatedImage(BaseModel):
    image_id: int
    filename: str
    annotated_path: str

class SyncSummary(BaseModel):
    high_defects: int
    medium_defects: int
    low_defects: int
    detections: List[ImageDetections]
    annotated_images: List[AnnotatedImage]

class SyncImageInfo(BaseModel):
    id: int
    filename: str
    status: str

class SyncImagesResponse2(BaseModel):
    message: str
    activity_status: str
    images: List[SyncImageInfo]
    summary: SyncSummary

# Response model for create_and_sync
class CreateAndSyncResponse(BaseModel):
    message: str
    activity: ActivityResponse     
    sync_result: SyncImagesResponse2
    range: Dict[str,Optional[str]]

class DefectTypewise(BaseModel):
    image_id: int
    patches_count: int
    scratches_count: int

class SyncSummaryFinal(BaseModel):  #  NEW
    high_defects_final: int
    medium_defects_final: int
    low_defects_final: int
    detections: List[ImageDetections]
    defect_count_typewise: List[DefectTypewise]
    annotated_images: List[AnnotatedImage]

class SyncResultResponse(BaseModel):  # NEW
    message: str
    activity_status: str
    images: List[SyncImageInfo]
    summary_final: SyncSummaryFinal
    range:Dict[str, Optional[str]]

class ActivityImageResponse(BaseModel):  # NEW
    id: int
    filename: str
    status: str
    original_blob_url: Optional[str]
    annotated_blob_url: Optional[str]
    created_at: datetime


class ActivityResponseGet(BaseModel):    # NEW
    id: str
    name: str
    status: str
    created_at: datetime
    images: List[ActivityImageResponse]


class ActivityDetailResponse(BaseModel):  # NEW (final wrapper for GET)
    activity: ActivityResponseGet
    sync_result: SyncResultResponse

