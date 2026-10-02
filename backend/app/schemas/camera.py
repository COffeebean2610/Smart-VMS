from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CameraBase(BaseModel):
    cameraName: str
    cameraType: str
    streamUrl: str
    location: str
    description: str = ""


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    cameraName: Optional[str] = None
    cameraType: Optional[str] = None
    streamUrl: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class CameraInDB(CameraBase):
    id: str
    status: str = "offline"
    fps: float = 0.0
    resolution: str = "Unknown"
    lastSeen: datetime
    createdAt: datetime