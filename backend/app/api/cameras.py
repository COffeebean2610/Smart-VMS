import logging
from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_database
from app.services.camera_service import CameraService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cameras", tags=["Cameras"])

from app.schemas.camera import CameraBase, CameraInDB, CameraUpdate

class TestCameraRequest(BaseModel):
    streamUrl: str


@router.get("/", response_model=List[CameraInDB])
async def get_cameras():
    db = get_database()
    cursor = db.cameras.find({}).sort("createdAt", -1)
    cameras = []
    async for cam in cursor:
        cam["id"] = str(cam["_id"])
        cam.pop("_id", None)

        if "streamSource" in cam:
            cam["streamUrl"] = cam.pop("streamSource")

        cam.setdefault("status", "offline")
        cam.setdefault("fps", 0)
        cam.setdefault("resolution", "Unknown")
        cam.setdefault("description", "")
        cam.setdefault("cameraType", "Unknown")
        
        # handle lastSeen and createdAt missing fields
        cam.setdefault("lastSeen", cam.get("createdAt", datetime.utcnow()))
        cam.setdefault("createdAt", cam.get("lastSeen"))

        cameras.append(CameraInDB(**cam))
    return cameras


@router.post("/", response_model=CameraInDB)
async def create_camera(camera: CameraBase):
    db = get_database()

    # Defaults
    status = "offline"
    fps = 0.0
    resolution = "Unknown"

    # If adding, let's optionally test it right away or just save it.
    url = camera.streamUrl if camera.cameraType != "Laptop Webcam" else "0"

    doc = {
        "cameraName": camera.cameraName,
        "cameraType": camera.cameraType,
        "streamUrl": url,
        "location": camera.location,
        "description": camera.description,
        "status": status,
        "fps": fps,
        "resolution": resolution,
        "lastSeen": datetime.utcnow(),
        "createdAt": datetime.utcnow(),
    }

    result = await db.cameras.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return CameraInDB(
    id=str(result.inserted_id),
    cameraName=doc["cameraName"],
    cameraType=doc["cameraType"],
    streamUrl=doc["streamUrl"],
    location=doc["location"],
    description=doc["description"],
    status=doc["status"],
    fps=doc["fps"],
    resolution=doc["resolution"],
    lastSeen=doc["lastSeen"],
    createdAt=doc["createdAt"],
)


@router.delete("/{id}")
async def delete_camera(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    db = get_database()
    result = await db.cameras.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"message": "Deleted successfully"}


@router.post("/test")
async def test_camera(req: TestCameraRequest):
    """
    Tests if a camera URL is valid and reachable using OpenCV.
    """
    url = req.streamUrl
    res = CameraService.test_connection(url)
    success = res[0]
    fps = res[1]
    resolution = res[2]
    error_reason = res[3] if len(res) > 3 else None

    if not success:
        if error_reason == "camera_blocked":
            return {
                "status": "failed",
                "errorReason": "camera_blocked",
                "message": "Camera access is blocked by Windows. Please enable Camera access for desktop apps in Windows Settings.",
            }
        return {"status": "failed", "errorReason": "failed", "message": "Could not connect to camera stream."}

    return {
        "status": "success",
        "fps": round(fps, 2),
        "resolution": f"{resolution[0]}x{resolution[1]}",
    }



@router.post("/connect/{id}")
async def connect_camera(id: str):
    """
    Connects the requested camera and starts its background capture & detection stream.
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")

    db = get_database()
    cam = await db.cameras.find_one({"_id": ObjectId(id)})
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    url = cam.get("streamUrl", "0")
    name = cam.get("cameraName", "Camera")

    # Start independent camera stream in CameraService
    camera_service = CameraService()
    camera_service.get_or_create_stream(id, name, url)

    # Update status in DB
    await db.cameras.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "online", "lastSeen": datetime.utcnow()}},
    )

    return {"message": f"Successfully connected to {name}", "cameraId": id}


@router.post("/disconnect/{id}")
async def disconnect_camera(id: str):
    """
    Disconnects the requested camera stream.
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")

    db = get_database()
    cam = await db.cameras.find_one({"_id": ObjectId(id)})
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    camera_service = CameraService()
    camera_service.stop_stream(id)

    await db.cameras.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "offline", "lastSeen": datetime.utcnow()}},
    )

    return {"message": f"Successfully disconnected {cam.get('cameraName', 'Camera')}", "cameraId": id}

