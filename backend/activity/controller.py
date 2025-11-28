from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from db import get_db
from activity import service
from activity.schema import (
    ActivityCreate,
    ActivityResponse,
    SyncResponse,
    SummaryResponse,
    DeleteResponse,
    SyncImagesResponse,
    CreateAndSyncResponse,
    SyncImagesResponse2,
    ActivityDetailResponse
)


router = APIRouter(prefix="/activity", tags=["Activity"])


@router.post("/v1", response_model=DeleteResponse)  # schema is same as that of DeleteResponse
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)):
    try:
        resp = service.create_activity(db, payload.name)
        return resp
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error creating activity: {str(e)}"
        )


@router.get("/v1", response_model=List[ActivityResponse])
def list_activities(db: Session = Depends(get_db)):
    try:
        return service.list_activities(db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error listing activities: {str(e)}"
        )


@router.get("/v1/{activity_id}", response_model=ActivityResponse)
def get_activity(activity_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_activity(db, activity_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error fetching activity: {str(e)}"
        )


@router.post("/v1/{activity_id}/sync", response_model=SyncResponse)
def sync_images(activity_id: str, db: Session = Depends(get_db)):
    try:
        return service.sync_images(db, activity_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error syncing images: {str(e)}"
        )


@router.get("/v1/{activity_id}/summary", response_model=SummaryResponse)
def get_activity_summary(activity_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_activity_summary(db, activity_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error generating summary: {str(e)}"
        )


@router.delete("/v1/{activity_id}", response_model=DeleteResponse)
def delete_activity(activity_id: str, db: Session = Depends(get_db)):
    try:
        return service.delete_activity(db, activity_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error deleting activity: {str(e)}"
        )


@router.post("/v1/upload")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        return await service.upload_image(file)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error uploading image: {str(e)}"
        )

@router.delete("/v1/{activity_id}/blob", response_model=DeleteResponse)
def delete_activity(activity_id: str, db: Session = Depends(get_db)):
    try:
        resp = service.delete_activity(db, activity_id)
        return resp
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error deleting activity: {str(e)}")
    
#--------------------------------------------DEMO-------------------------------------------------------------#

# Create activity
@router.post("/", response_model=ActivityResponse)
def create_activity_demo(db: Session = Depends(get_db)):
    try:
        return service.create_activity_demo(db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error creating activity: {str(e)}")

# List activities
@router.get("/", response_model=list[ActivityResponse])
def list_activities_demo(db: Session = Depends(get_db)):
    try:
        return service.list_activities_demo(db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error listing activities: {str(e)}")

# Get activity by id
@router.get("/{activity_id}", response_model=ActivityDetailResponse)
def get_activity_demo(activity_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_activity_demo(db, activity_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching activity: {str(e)}")

# Delete activity
@router.delete("/{activity_id}", response_model=DeleteResponse)
def delete_activity_demo(activity_id: str, db: Session = Depends(get_db)):
    try:
        return service.delete_activity_demo(db, activity_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error deleting activity: {str(e)}")

# Demo sync
@router.post("/{activity_id}/sync-demo", response_model=SyncImagesResponse)
def sync_demo(activity_id: str, db: Session = Depends(get_db)):
    try:
        return service.sync_images_demo(db, activity_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error syncing demo images: {str(e)}")

# Demo sync2
@router.post("/{activity_id}/sync-demo2", response_model=SyncImagesResponse2)
def sync_demo2(activity_id: str, db: Session = Depends(get_db)):
    try:
        return service.sync_images_demo2(db, activity_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error syncing demo images: {str(e)}")

# create and sync
@router.post("/create-and-sync", response_model=CreateAndSyncResponse)
def create_and_sync(from_value: str = None, to_value: str = None, db: Session = Depends(get_db)):
    try:
        return service.create_and_sync(db, from_value=from_value, to_value=to_value)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error syncing activity: {str(e)}")
