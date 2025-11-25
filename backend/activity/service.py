import os
import uuid
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from db import Activity, ActivityImage
from azure.storage.blob import BlobServiceClient, ContentSettings
from models.detector import detect_defects
from utils.logger import log_audit
from utils.config_loader import load_config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "nexus-sdd-images")

if not AZURE_STORAGE_CONNECTION_STRING:
    raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not set")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

ORIGINAL_PREFIX = "original/"
ANNOTATED_PREFIX = "annotated/"



def _blob_url(blob_name: str) -> str:
    return container_client.get_blob_client(blob_name).url


def create_activity(db: Session, name: str):
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Activity name is required")
    activity_id = str(uuid.uuid4())
    activity = Activity(id=activity_id, name=name.strip(), status="pending")
    db.add(activity)
    db.commit()
    log_audit(f"Created activity: {name}", "data/logs/audit.log")
    return {"message": "Activity created", "activity_id": activity_id}


def list_activities(db: Session):
    activities = db.query(Activity).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "status": a.status,
            "created_at": a.created_at,
            "images": [
                {
                    "id": img.id,
                    "filename": img.filename,
                    "status": img.status,
                    "original_blob_url": img.original_blob_url,
                    "annotated_blob_url": img.annotated_blob_url,
                    "created_at": img.created_at,
                }
                for img in sorted(a.images, key=lambda i: i.created_at, reverse=True)  # newest first
            ],
        }
        for a in activities
    ]


def get_activity(db: Session, activity_id: str):
    activity = db.query(Activity).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return {
        "id": activity.id,
        "name": activity.name,
        "status": activity.status,
        "created_at": activity.created_at,
        "images": [
            {
                "id": img.id,
                "filename": img.filename,
                "status": img.status,
                "original_blob_url": img.original_blob_url,
                "annotated_blob_url": img.annotated_blob_url,
                "created_at": img.created_at,
            }
            for img in sorted(activity.images, key=lambda i: i.created_at, reverse=True)  # newest first
        ],
    }


def sync_images(db: Session, activity_id: str):
    activity = db.query(Activity).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity.status = "in-progress"
    db.commit()
    log_audit(f"Listing blobs of activity: {activity_id} successfully", "data/logs/audit.log")

    try:
        blobs = list(container_client.list_blobs(name_starts_with=ORIGINAL_PREFIX))
    except Exception as e:
        log_audit(f"Failed to list blobs of activity {activity_id}; Error: {str(e)}", "data/logs/audit.log")
        raise HTTPException(status_code=502, detail="Failed to list blobs from container")

    new_count, processed_count, error_count = 0, 0, 0

    for blob in blobs:
        filename_only = blob.name.split("/")[-1]
        exists = db.query(ActivityImage).filter_by(filename=filename_only, activity_id=activity_id).first()
        if exists:
            continue

        new_count += 1
        image = ActivityImage(activity_id=activity_id, filename=filename_only, status="processing")
        db.add(image)
        db.commit()

        try:
            # Original blob URL
            original_blob_name = f"{ORIGINAL_PREFIX}{filename_only}"
            image.original_blob_url = _blob_url(original_blob_name)
            db.commit()

            # Download original image bytes
            original_blob = container_client.get_blob_client(original_blob_name)
            image_bytes = original_blob.download_blob().readall()

            # Run defect detection
            result = detect_defects(image_bytes)
            detections = result.get("detections", [])
            annotated_bytes = result.get("result_image_bytes", b"")

            # Severity counts
            high = sum(1 for d in detections if d.get("confidence", 0) >= 0.8)
            medium = sum(1 for d in detections if 0.5 <= d.get("confidence", 0) < 0.8)
            low = sum(1 for d in detections if d.get("confidence", 0) < 0.5)

            image.high_defects = high
            image.medium_defects = medium
            image.low_defects = low
            image.detections = detections

            if detections and annotated_bytes:
                annotated_blob_name = f"{ANNOTATED_PREFIX}{filename_only}"
                annotated_client = container_client.get_blob_client(annotated_blob_name)
                annotated_client.upload_blob(
                    annotated_bytes,
                    overwrite=True,
                    content_settings=ContentSettings(content_type="image/png")  # inline display
                )
                image.status = "defects_detected"
                image.annotated_blob_url = _blob_url(annotated_blob_name)
            else:
                image.status = "no_defects"
                image.annotated_blob_url = None

            db.commit()
            processed_count += 1

        except Exception as e:
            image.status = "error"
            db.commit()
            error_count += 1
            log_audit(f"Sync Error {str(e)} for {filename_only} in activity {activity_id}", "data/logs/audit.log")

    # Final activity status
    if error_count > 0:
        activity.status = "error"
    else:
        all_done = all(img.status in ["no_defects", "defects_detected"] for img in activity.images)
        activity.status = "completed" if all_done else "in-progress"
    db.commit()

    final_resp = {
        "message": "Sync complete",
        "activity_status": activity.status,
        "new_images_found": new_count,
        "processed_images": processed_count,
        "error_images": error_count,
    }
    log_audit(f"Sync completed for activity {activity_id}", "data/logs/audit.log")
    return final_resp


def get_activity_summary(db: Session, activity_id: str):
    activity = db.query(Activity).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    summary = {
        "activity_id": activity_id,
        "high_defects": sum(img.high_defects or 0 for img in activity.images),
        "medium_defects": sum(img.medium_defects or 0 for img in activity.images),
        "low_defects": sum(img.low_defects or 0 for img in activity.images),
        "defect_images": [],
        "activity_status": activity.status,
    }

    for image in activity.images:
        if image.status == "defects_detected":
            summary["defect_images"].append({
                "filename": image.filename,
                "original_blob_url": image.original_blob_url,
                "annotated_blob_url": image.annotated_blob_url,
                "detections": image.detections or [],
            })

    log_audit(f"Summary generated for activity {activity_id}; Defect images:{str(len(summary['defect_images']))}", "data/logs/audit.log")
    return summary


def delete_activity(db: Session, activity_id: str):
    activity = db.query(Activity).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Only delete DB records
    db.query(ActivityImage).filter_by(activity_id=activity_id).delete()
    db.query(Activity).filter_by(id=activity_id).delete()
    db.commit()

    log_audit(f"Deleted activity {activity_id} successfully (DB only)", "data/logs/audit.log")
    return {"message": "Activity deleted", "activity_id": activity_id}


# Upload images to blob
async def upload_image(file: UploadFile):
    """
    Upload a single image into Azure Blob Storage under the 'original/' prefix.
    Returns blob URL and blob name.
    """
    try:
        blob_name = f"{ORIGINAL_PREFIX}{uuid.uuid4()}_{file.filename}"
        blob_client = container_client.get_blob_client(blob_name)

        data = await file.read()
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type)  # inline display
        )

        log_audit(f"Uploaded image {blob_name} successfully", "data/logs/audit.log")

        return {
            "message": "Upload successful",
            "blob_url": blob_client.url,
            "blob_name": blob_name
        }
    except Exception as e:
        log_audit(f"Upload failed for {file.filename}; Error: {str(e)}", "data/logs/audit.log")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

def delete_activity_blob(db: Session, activity_id: str):
    activity = db.query(Activity).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    for img in activity.images:
        filename_only = img.filename
        try:
            original_blob_name = f"{ORIGINAL_PREFIX}{filename_only}"
            container_client.delete_blob(original_blob_name)
            log_audit(f"Deleted original blob {original_blob_name} successfully of activity {activity_id}", "data/logs/audit.log")
        except Exception as e:
            log_audit(f"Failed to delete original blob {original_blob_name} of activity {activity_id}; Error: {str(e)}", "data/logs/audit.log")

        if img.annotated_blob_url:
            try:
                annotated_blob_name = f"{ANNOTATED_PREFIX}{filename_only}"
                container_client.delete_blob(annotated_blob_name)
                log_audit(f"Deleted annotated blob {annotated_blob_name} successfully of activity {activity_id}", "data/logs/audit.log")
            except Exception as e:
                log_audit(f"Failed to delete annotated blob {annotated_blob_name} of activity {activity_id}; Error: {str(e)}", "data/logs/audit.log")

    db.query(ActivityImage).filter_by(activity_id=activity_id).delete()
    db.query(Activity).filter_by(id=activity_id).delete()
    db.commit()

    log_audit(f"Deleted activity {activity_id} successfully", "data/logs/audit.log")
    return {"message": "Activity deleted", "activity_id": activity_id}

#-----------------------------------------------------------Demo------------------------------------------------------------------------#

from config.service import get_thresholds
from pathlib import Path
from config.settings import DEMO_FOLDER
config = load_config()
low_thr = config["low"]
high_thr = config["high"]

BASE_DIR = Path(__file__).resolve().parent.parent



def create_activity_demo(db: Session):
    try:
        activity_id = str(uuid.uuid4())
        random_suffix=str(uuid.uuid4())[:8]
        name=f"Activity_{random_suffix}"
        activity = Activity(id=activity_id, name=name, status="pending")
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create activity: {str(e)}")

def list_activities_demo(db: Session):
    try:
        return db.query(Activity).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list activities: {str(e)}")


def get_activity_demo(db: Session, activity_id: str):
    low_thr, high_thr, _ = get_thresholds()
    activity = db.query(Activity).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    images = db.query(ActivityImage).filter_by(activity_id=activity_id).all()

    # Recalculate defect counts using detections + current thresholds
    total_low = total_medium = total_high = 0
    detections_summary = []
    annotated_images = []

    sync_images_view = []

    for img in images:
        img_low = img_med = img_high = 0
        if img.detections:
            for d in img.detections:
                conf = float(d.get("confidence", 0.0))
                if conf >= high_thr:
                    img_high += 1
                elif conf >= low_thr:
                    img_med += 1
                else:
                    img_low += 1
        total_low += img_low
        total_medium += img_med
        total_high += img_high

        sync_images_view.append({
            "id": img.id,
            "filename": img.filename,
            "status": img.status
        })

        if img.detections:
            detections_summary.append({
                "image_id": img.id,
                "filename": img.filename,
                "detections": img.detections
            })
        if img.annotated_blob_url:
            annotated_images.append({
                "image_id": img.id,
                "filename": img.filename,
                "annotated_path": img.annotated_blob_url
            })

    summary_final = {
        "high_defects_final": total_high,
        "medium_defects_final": total_medium,
        "low_defects_final": total_low,
        "detections": detections_summary,
        "annotated_images": annotated_images,
    }

    return {
        "activity": {
            "id": activity.id,
            "name": activity.name,
            "status": activity.status,
            "created_at": activity.created_at,
            "images": [
                {
                    "id": img.id,
                    "filename": img.filename,
                    "status": img.status,
                    "original_blob_url": img.original_blob_url,
                    "annotated_blob_url": img.annotated_blob_url,
                    "created_at": img.created_at,
                }
                for img in images
            ]
        },
        "sync_result": {
            "message": "Demo sync complete",
            "activity_status": activity.status,
            "images": sync_images_view,
            "summary_final": summary_final
        }
    }


def delete_activity_demo(db: Session, activity_id: str):
    activity = db.query(Activity).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Only delete DB records
    db.query(ActivityImage).filter_by(activity_id=activity_id).delete()
    db.query(Activity).filter_by(id=activity_id).delete()
    db.commit()

    log_audit(f"Deleted activity {activity_id} successfully (DB only)", "data/logs/audit.log")
    return {"message": "Activity deleted", "activity_id": activity_id}


def sync_images_demo(db: Session, activity_id: str):
    activity = db.query(Activity).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity.status = "in-progress"
    db.commit()

    demo_files = {
        "image1.png": True,
        "image2.jpg": False,
        "image3.jpg": False,
        "image4.jpeg": False,
    }

    summary = {
        "high_defects": 0,
        "medium_defects": 0,
        "low_defects": 0,
        "detections": [],
        "annotated_image_path": None,
    }

    for fname, is_defect in demo_files.items():
        file_path = DEMO_FOLDER / fname
        if not file_path.exists():
            continue
        
        image = db.query(ActivityImage).filter_by(activity_id=activity_id, filename=fname).first()
        if image:
            continue

        image = ActivityImage(activity_id=activity_id, filename=fname, status="processing")
        db.add(image)
        db.commit()
        if not is_defect:
            image.status = "no_defects"
            db.commit()
            continue

        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()

            result = detect_defects(image_bytes)
            detections = result.get("detections", [])
            annotated_bytes = result.get("result_image_bytes", b"")

            image.high_defects = sum(1 for d in detections if d.get("confidence", 0) >= high_thr)
            image.medium_defects = sum(1 for d in detections if low_thr <= d.get("confidence", 0) < high_thr)
            image.low_defects = sum(1 for d in detections if d.get("confidence", 0) < low_thr)
            image.detections = detections

            summary["high_defects"] += image.high_defects or 0
            summary["medium_defects"] += image.medium_defects or 0
            summary["low_defects"] += image.low_defects or 0

            if detections and annotated_bytes:
                annotated_path = DEMO_FOLDER / f"annotated_{fname}"
                print(annotated_path)
                with open(annotated_path, "wb") as f:
                    f.write(annotated_bytes)
                image.status = "defects_detected"
                image.annotated_blob_url = annotated_path.as_posix()
                print(image.annotated_blob_url)
                summary["annotated_image_path"] = annotated_path.as_posix()
                defect_counts = {}
                for d in detections:
                    defect_type = d.get("class", "unknown")
                    defect_counts[defect_type] = defect_counts.get(defect_type, 0) + 1
                summary["detections"].append(defect_counts)
            else:
                image.status = "no_defects"

            db.commit()

        except Exception as e:
            image.status = "error"
            db.commit()
            # raise HTTPException(status_code=500, detail=f"Error processing defect image: {str(e)}")
            continue
            

    activity.status = "completed"
    db.commit()
    db.refresh(activity)
    images = db.query(ActivityImage).filter_by(activity_id=activity_id).all()

    summary = {
        "high_defects": sum(img.high_defects or 0 for img in images),
        "medium_defects": sum(img.medium_defects or 0 for img in images),
        "low_defects": sum(img.low_defects or 0 for img in images),
        "detections": [img.detections for img in images if img.detections],
        "annotated_image_path": next((Path(img.annotated_blob_url).as_posix() for img in images if img.annotated_blob_url), None),
    }

    return {
        "message": "Demo sync complete",
        "activity_status": activity.status,
        "images": [{"filename": img.filename, "status": img.status} for img in images],
        "summary": summary,
    }

def sync_images_demo2(db: Session, activity_id: str):
    activity = db.query(Activity).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity.status = "in-progress"
    db.commit()

    demo_files = {
        "image1.png": True,
        "image2.jpg": False,
        "image3.jpg": False,
        "image4.jpeg": False,
    }

    for fname, is_defect in demo_files.items():
        file_path = DEMO_FOLDER / fname
        if not file_path.exists():
            continue

        # Skip if image already exists (idempotent sync)
        image = db.query(ActivityImage).filter_by(activity_id=activity_id, filename=fname).first()
        if image:
            continue

        image = ActivityImage(activity_id=activity_id, filename=fname, status="processing")
        db.add(image)
        db.commit()

        if not is_defect:
            image.status = "no_defects"
            db.commit()
            continue

        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()

            result = detect_defects(image_bytes)
            detections = result.get("detections", [])
            annotated_bytes = result.get("result_image_bytes", b"")

            image.high_defects = sum(1 for d in detections if d.get("confidence", 0) >= high_thr)
            image.medium_defects = sum(1 for d in detections if low_thr <= d.get("confidence", 0) < high_thr)
            image.low_defects = sum(1 for d in detections if d.get("confidence", 0) < low_thr)
            image.detections = detections

            if detections and annotated_bytes:
                annotated_path = DEMO_FOLDER / f"annotated_{fname}"
                with open(annotated_path, "wb") as f:
                    f.write(annotated_bytes)
                image.status = "defects_detected"
                image.annotated_blob_url = f"/demo_images/annotated_{fname}"
            else:
                image.status = "no_defects"

            db.commit()

        except Exception as e:
            image.status = "error"
            db.commit()
            continue

    activity.status = "completed"
    db.commit()
    db.refresh(activity)
    images = db.query(ActivityImage).filter_by(activity_id=activity_id).all()

    summary = {
        "high_defects": sum(img.high_defects or 0 for img in images),
        "medium_defects": sum(img.medium_defects or 0 for img in images),
        "low_defects": sum(img.low_defects or 0 for img in images),
        "detections": [
            {
                "image_id": img.id,
                "filename": img.filename,
                "detections": img.detections
            }
            for img in images if img.detections
        ],
        "annotated_images": [
            {
                "image_id": img.id,
                "filename": img.filename,
                "annotated_path": img.annotated_blob_url
            }
            for img in images if img.annotated_blob_url
        ],
    }

    return {
        "message": "Demo sync complete",
        "activity_status": activity.status,
        "images": [{"id": img.id, "filename": img.filename, "status": img.status} for img in images],
        "summary": summary,
    }

def create_and_sync(db: Session):
    try:
        activity=create_activity_demo(db)
        result=sync_images_demo2(db, activity.id)
        return {
            "message": "Activity created and synced",
            "activity": activity,
            "sync_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")
