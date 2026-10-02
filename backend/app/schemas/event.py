from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class EventBase(BaseModel):
    cameraId: str = Field(...)
    cameraName: Optional[str] = "Default Webcam"
    eventType: str = Field(...)
    detectionSource: Optional[str] = "person"
    confidence: float = Field(...)
    snapshot: Optional[str] = None
    videoPath: Optional[str] = None
    recordingId: Optional[str] = None
    videoTimestamp: Optional[float] = 0.0
    roiId: Optional[str] = None
    roiName: Optional[str] = None
    bbox: Optional[List[int]] = None
    status: str = Field(default="active")


class EventCreate(EventBase):
    pass


class EventInDB(EventBase):
    id: str = Field(alias="_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

