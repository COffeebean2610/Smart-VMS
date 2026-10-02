import os
import shutil
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter

from app.db.database import get_database
from app.core.paths import get_storage_dir

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_model=Dict[str, Any])
async def get_dashboard_summary():
    db = get_database()

    total_cameras = await db.cameras.count_documents({})
    online_cameras = await db.cameras.count_documents({"status": "online"})
    offline_cameras = total_cameras - online_cameras

    # Intrusions Today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    intrusions_today = await db.events.count_documents({"timestamp": {"$gte": today}})

    # Weekly Intrusions
    week_ago = today - timedelta(days=7)
    weekly_intrusions = await db.events.count_documents(
        {"timestamp": {"$gte": week_ago}}
    )

    active_alerts = await db.events.count_documents({"status": "active"})
    recordings_stored = await db.recordings.count_documents({})

    # Storage Usage using shutil
    storage_path = str(get_storage_dir())
    total, used, free = shutil.disk_usage(storage_path)

    storage_used_gb = round(used / (1024**3), 2)
    storage_total_gb = round(total / (1024**3), 2)
    storage_used_percent = round((used / total) * 100, 1) if total > 0 else 0

    # Detection Accuracy Mock (since YOLO confidence isn't stored as accuracy)
    detection_accuracy = 98.5

    # Avg Confidence
    pipeline = [{"$group": {"_id": None, "avgConfidence": {"$avg": "$confidence"}}}]
    avg_cursor = db.events.aggregate(pipeline)
    avg_conf = 0
    async for doc in avg_cursor:
        avg_conf = round(doc.get("avgConfidence", 0) * 100, 1)

    return {
        "totalCameras": total_cameras,
        "onlineCameras": online_cameras,
        "offlineCameras": offline_cameras,
        "intrusionsToday": intrusions_today,
        "weeklyIntrusions": weekly_intrusions,
        "activeAlerts": active_alerts,
        "recordingsStored": recordings_stored,
        "storageUsedGB": storage_used_gb,
        "storageTotalGB": storage_total_gb,
        "storageUsedPercent": storage_used_percent,
        "detectionAccuracy": detection_accuracy,
        "averageConfidence": avg_conf,
    }


@router.get("/charts", response_model=Dict[str, Any])
async def get_dashboard_charts():
    db = get_database()

    # 1. Events Per Hour (Line Chart)
    # Group events by hour for today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline_hourly = [
        {"$match": {"timestamp": {"$gte": today}}},
        {"$group": {"_id": {"$hour": "$timestamp"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    hourly_cursor = db.events.aggregate(pipeline_hourly)
    events_per_hour = []
    async for h in hourly_cursor:
        events_per_hour.append({"hour": f"{h['_id']:02d}:00", "events": h["count"]})

    # 2. Intrusions by Camera (Bar Chart)
    pipeline_camera = [
        {"$group": {"_id": "$cameraId", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    cam_cursor = db.events.aggregate(pipeline_camera)
    intrusions_by_camera = []
    async for c in cam_cursor:
        intrusions_by_camera.append({"camera": c["_id"], "intrusions": c["count"]})

    # 3. Storage Usage (Donut Chart)
    # Same as summary
    storage_path = str(get_storage_dir())
    total, used, free = shutil.disk_usage(storage_path)
    storage_usage = [
        {"name": "Used", "value": round(used / (1024**3), 2)},
        {"name": "Free", "value": round(free / (1024**3), 2)},
    ]

    # 4. Detection Distribution (Pie Chart)
    pipeline_type = [{"$group": {"_id": "$eventType", "count": {"$sum": 1}}}]
    type_cursor = db.events.aggregate(pipeline_type)
    detection_distribution = []
    async for t in type_cursor:
        detection_distribution.append({"name": t["_id"], "value": t["count"]})

    # 5. Weekly Intrusion Trend (Area Chart)
    week_ago = today - timedelta(days=7)
    pipeline_weekly = [
        {"$match": {"timestamp": {"$gte": week_ago}}},
        {"$group": {"_id": {"$dayOfWeek": "$timestamp"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    week_cursor = db.events.aggregate(pipeline_weekly)

    # Map day of week (1=Sun, 7=Sat) to String
    days_map = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
    weekly_trend = []
    async for d in week_cursor:
        weekly_trend.append(
            {"day": days_map.get(d["_id"], "Unknown"), "intrusions": d["count"]}
        )

    return {
        "eventsPerHour": events_per_hour,
        "intrusionsByCamera": intrusions_by_camera,
        "storageUsage": storage_usage,
        "detectionDistribution": detection_distribution,
        "weeklyTrend": weekly_trend,
    }
