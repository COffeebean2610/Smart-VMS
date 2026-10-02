from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DetectionZoneBase(BaseModel):
    cameraId: str = Field(...)
    zoneName: str = Field(...)
    coordinates: List[Dict[str, float]] = Field(
        default_factory=list
    )  # e.g., [{"x": 0.1, "y": 0.2}]


class DetectionZoneCreate(DetectionZoneBase):
    pass


class DetectionZoneUpdate(BaseModel):
    zoneName: Optional[str] = None
    coordinates: Optional[List[Dict[str, float]]] = None


class DetectionZoneInDB(DetectionZoneBase):
    id: str = Field(alias="_id")
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
