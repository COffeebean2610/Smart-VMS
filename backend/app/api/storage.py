import os
import shutil
from typing import Any, Dict

from fastapi import APIRouter

from app.db.database import get_database

from app.core.paths import get_storage_dir

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.get("/", response_model=Dict[str, Any])
async def get_storage_info():
    db = get_database()

    storage_path = str(get_storage_dir())
    total, used, free = shutil.disk_usage(storage_path)

    total_gb = round(total / (1024**3), 2)
    used_gb = round(used / (1024**3), 2)
    free_gb = round(free / (1024**3), 2)
    used_percent = round((used / total) * 100, 1) if total > 0 else 0

    num_recordings = await db.recordings.count_documents({})
    num_snapshots = await db.events.count_documents({"snapshot": {"$ne": None}})

    # Oldest and Newest Recordings
    oldest_rec = await db.recordings.find_one({}, sort=[("startTime", 1)])
    newest_rec = await db.recordings.find_one({}, sort=[("startTime", -1)])

    oldest = oldest_rec["startTime"] if oldest_rec else None
    newest = newest_rec["startTime"] if newest_rec else None

    # Storage Trend Mock (Daily growth)
    trend = [
        {"day": "Mon", "gb": used_gb * 0.7},
        {"day": "Tue", "gb": used_gb * 0.75},
        {"day": "Wed", "gb": used_gb * 0.8},
        {"day": "Thu", "gb": used_gb * 0.85},
        {"day": "Fri", "gb": used_gb * 0.9},
        {"day": "Sat", "gb": used_gb * 0.95},
        {"day": "Sun", "gb": used_gb},
    ]

    return {
        "totalGB": total_gb,
        "usedGB": used_gb,
        "freeGB": free_gb,
        "usedPercent": used_percent,
        "numRecordings": num_recordings,
        "numSnapshots": num_snapshots,
        "oldestRecording": oldest,
        "newestRecording": newest,
        "trend": trend,
    }
