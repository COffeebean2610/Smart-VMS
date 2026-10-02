import os
from datetime import datetime, timedelta
from typing import List

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.db.database import get_database
from app.schemas.event import EventCreate, EventInDB
from app.core.paths import resolve_storage_relative_path

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/", response_model=List[EventInDB])
async def get_events(limit: int = 50):
    db = get_database()
    events_cursor = db.events.find({}).sort("timestamp", -1).limit(limit)
    events = []
    async for event in events_cursor:
        event["_id"] = str(event["_id"])
        events.append(EventInDB(**event))
    return events


@router.get("/{id}", response_model=EventInDB)
async def get_event(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid event ID")
    db = get_database()
    event = await db.events.find_one({"_id": ObjectId(id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event["_id"] = str(event["_id"])
    return EventInDB(**event)


@router.get("/{id}/snapshot")
async def get_event_snapshot(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid event ID")
    db = get_database()
    event = await db.events.find_one({"_id": ObjectId(id)})
    if not event or not event.get("snapshot"):
        raise HTTPException(status_code=404, detail="Event snapshot not found")
    file_path = str(resolve_storage_relative_path(event["snapshot"]))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Snapshot file missing on disk")
    return FileResponse(file_path, media_type="image/jpeg")


@router.post("/", response_model=EventInDB, status_code=status.HTTP_201_CREATED)
async def create_event(event: EventCreate):
    db = get_database()
    event_dict = event.model_dump()
    event_dict["timestamp"] = datetime.utcnow()
    result = await db.events.insert_one(event_dict)
    event_dict["_id"] = str(result.inserted_id)
    return EventInDB(**event_dict)


@router.delete("/bulk/{filter_type}", status_code=status.HTTP_200_OK)
async def bulk_delete_events(filter_type: str):
    db = get_database()
    query = {}

    now = datetime.utcnow()
    if filter_type == "day":
        query = {"timestamp": {"$lt": now - timedelta(days=1)}}
    elif filter_type == "week":
        query = {"timestamp": {"$lt": now - timedelta(weeks=1)}}
    elif filter_type == "month":
        query = {"timestamp": {"$lt": now - timedelta(days=30)}}
    elif filter_type == "all":
        query = {}
    else:
        raise HTTPException(status_code=400, detail="Invalid filter type")

    # Find files to delete
    cursor = db.events.find(query)
    deleted_files = 0
    async for event in cursor:
        if event.get("snapshot"):
            file_path = str(resolve_storage_relative_path(event["snapshot"]))
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files += 1

    result = await db.events.delete_many(query)
    return {"deletedRecords": result.deleted_count, "deletedFiles": deleted_files}


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid event ID")
    db = get_database()

    event = await db.events.find_one({"_id": ObjectId(id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Delete physical file
    if event.get("snapshot"):
        file_path = str(resolve_storage_relative_path(event["snapshot"]))
        if os.path.exists(file_path):
            os.remove(file_path)

    await db.events.delete_one({"_id": ObjectId(id)})
    return None
