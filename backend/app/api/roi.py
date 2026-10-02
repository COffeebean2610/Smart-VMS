from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status

from app.db.database import get_database
from app.schemas.zone import DetectionZoneCreate, DetectionZoneInDB, DetectionZoneUpdate
from app.services.frame_processor import FrameProcessor

router = APIRouter(prefix="/roi", tags=["Detection Zones (ROI)"])


@router.get("/", response_model=List[DetectionZoneInDB])
async def get_zones():
    db = get_database()
    zones_cursor = db.detection_zones.find({})
    zones = []
    async for zone in zones_cursor:
        zone["_id"] = str(zone["_id"])
        zones.append(DetectionZoneInDB(**zone))
    return zones


@router.post("/", response_model=DetectionZoneInDB, status_code=status.HTTP_201_CREATED)
async def create_zone(zone: DetectionZoneCreate):
    db = get_database()
    zone_dict = zone.model_dump()
    zone_dict["createdAt"] = datetime.utcnow()
    result = await db.detection_zones.insert_one(zone_dict)
    zone_dict["_id"] = str(result.inserted_id)
    await FrameProcessor().update_rois()
    return DetectionZoneInDB(**zone_dict)


@router.put("/{id}", response_model=DetectionZoneInDB)
async def update_zone(id: str, zone_update: DetectionZoneUpdate):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid zone ID")
    db = get_database()
    update_data = {k: v for k, v in zone_update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await db.detection_zones.update_one(
        {"_id": ObjectId(id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Detection Zone not found")

    updated_zone = await db.detection_zones.find_one({"_id": ObjectId(id)})
    updated_zone["_id"] = str(updated_zone["_id"])
    await FrameProcessor().update_rois()
    return DetectionZoneInDB(**updated_zone)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid zone ID")
    db = get_database()
    result = await db.detection_zones.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Detection Zone not found")
    await FrameProcessor().update_rois()
    return None
