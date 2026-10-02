import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.db.database import get_database
from app.core.paths import resolve_storage_relative_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recordings", tags=["Recordings"])


class RecordingInDB(BaseModel):
    id: str
    cameraId: str
    filePath: str
    startTime: datetime
    endTime: datetime
    duration: float
    fileSize: int
    type: Optional[str] = "Intrusion Event"
    createdAt: datetime


@router.get("/", response_model=List[RecordingInDB])
async def get_recordings(limit: int = 100):
    db = get_database()
    cursor = db.recordings.find({}).sort("createdAt", -1).limit(limit)
    recordings = []
    async for rec in cursor:
        rec["id"] = str(rec["_id"])
        recordings.append(RecordingInDB(**rec))
    return recordings


@router.get("/{id}", response_model=RecordingInDB)
async def get_recording(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid recording ID")
    db = get_database()
    rec = await db.recordings.find_one({"_id": ObjectId(id)})
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")
    rec["id"] = str(rec["_id"])
    return RecordingInDB(**rec)


@router.get("/{id}/stream")
async def stream_recording(id: str):
    logger.info(f"--- Stream Request for Recording {id} ---")
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid recording ID")
    db = get_database()
    rec = await db.recordings.find_one({"_id": ObjectId(id)})
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    absolute_path = str(resolve_storage_relative_path(rec["filePath"]))

    logger.info(f"Requested File: {absolute_path}")
    logger.info(f"File Exists: {os.path.exists(absolute_path)}")

    if not os.path.exists(absolute_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    file_size = os.path.getsize(absolute_path)
    logger.info(f"File Size: {file_size} bytes")
    logger.info("MIME Type: video/mp4")

    return FileResponse(
        path=absolute_path,
        media_type="video/mp4",
        filename=os.path.basename(absolute_path),
        headers={"Accept-Ranges": "bytes"},
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recording(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid recording ID")
    db = get_database()

    rec = await db.recordings.find_one({"_id": ObjectId(id)})
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Delete physical file
    if rec.get("filePath"):
        file_path = str(resolve_storage_relative_path(rec["filePath"]))
        if os.path.exists(file_path):
            os.remove(file_path)

    await db.recordings.delete_one({"_id": ObjectId(id)})
    return None


@router.delete("/bulk/{filter_type}", status_code=status.HTTP_200_OK)
async def bulk_delete_recordings(filter_type: str):
    db = get_database()
    query = {}

    now = datetime.utcnow()
    if filter_type == "day":
        query = {"startTime": {"$lt": now - timedelta(days=1)}}
    elif filter_type == "week":
        query = {"startTime": {"$lt": now - timedelta(weeks=1)}}
    elif filter_type == "month":
        query = {"startTime": {"$lt": now - timedelta(days=30)}}
    elif filter_type == "all":
        query = {}
    else:
        raise HTTPException(status_code=400, detail="Invalid filter type")

    # Find files to delete
    cursor = db.recordings.find(query)
    deleted_files = 0
    async for rec in cursor:
        if rec.get("filePath"):
            file_path = str(resolve_storage_relative_path(rec["filePath"]))
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files += 1

    result = await db.recordings.delete_many(query)
    return {"deletedRecords": result.deleted_count, "deletedFiles": deleted_files}
