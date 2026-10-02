import asyncio
import logging
import os
import time
from datetime import datetime

import cv2
from bson import ObjectId

from app.db.database import get_database
from app.services.recording_service import RecordingService
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class EventService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # State tracking: key = (str(camera_id), str(roi_id))
        # value = {"is_occupied": bool, "last_event_time": float}
        self.roi_states = {}
        self.cooldown_period = 4.0  # seconds cooldown between events for same ROI
        from app.core.paths import get_snapshots_dir
        self.snapshots_dir = str(get_snapshots_dir())
        self.recording_service = RecordingService()
        self.telegram_service = TelegramService()

    def update_roi_absence(self, camera_id: str, roi_id: str):
        """
        Called when ROI has no intrusion on a frame.
        Resets occupied state so re-entering the ROI will trigger a new event.
        """
        key = (str(camera_id), str(roi_id))
        state = self.roi_states.get(key)
        if state and state.get("is_occupied"):
            state["is_occupied"] = False
            logger.info(
                f"[ROI] Intrusion ended for ROI '{roi_id}' on camera '{camera_id}'. State reset to OUTSIDE."
            )

    async def handle_intrusion(
        self,
        camera_id: str,
        camera_name: str,
        roi_id: str,
        roi_name: str,
        detection_source: str = "person",
        bbox: list = None,
        confidence: float = 1.0,
        frame=None,
        width: int = 640,
        height: int = 480,
        fps: float = 20.0,
    ):
        """
        Intrusion State Machine & Event Creation Pipeline:
        OUTSIDE -> DETECTED -> INSIDE
        """
        try:
            current_time = time.time()
            key = (str(camera_id), str(roi_id))

            if key not in self.roi_states:
                self.roi_states[key] = {
                    "is_occupied": False,
                    "last_event_time": 0.0,
                }

            state = self.roi_states[key]

            # If already inside, log suppression
            if state["is_occupied"]:
                logger.info(f"[EVENT SUPPRESSED]\nCamera={camera_id}\nROI={roi_id}\nreason=cooldown_occupied")
                return False

            # Cooldown check
            if current_time - state["last_event_time"] < self.cooldown_period:
                logger.info(f"[EVENT SUPPRESSED]\nCamera={camera_id}\nROI={roi_id}\nreason=cooldown")
                return False

            # State transition: OUTSIDE -> INSIDE
            state["is_occupied"] = True
            state["last_event_time"] = current_time

            logger.info(f"[EVENT SERVICE]\nCamera={camera_id}\nROI={roi_id}\nENTERED handle_intrusion()")
            current_loop = asyncio.get_running_loop()
            logger.info(f"FastAPI loop id: {id(current_loop)}")
            logger.info(f"EventService loop id: {id(current_loop)}")

            # 1. Create MongoDB Event Document FIRST
            event_timestamp = datetime.utcnow()
            event_id = ObjectId()
            event_doc = {
                "_id": event_id,
                "cameraId": str(camera_id),
                "cameraName": camera_name or f"Camera {camera_id}",
                "eventType": "intrusion",
                "detectionSource": detection_source,
                "confidence": round(float(confidence), 2),
                "snapshot": None,
                "videoPath": None,
                "recordingId": None,
                "status": "active",
                "roiId": str(roi_id),
                "roiName": roi_name or "ROI",
                "bbox": bbox or [],
                "timestamp": event_timestamp,
            }

            db = get_database()
            if db is not None:
                try:
                    insert_loop = asyncio.get_running_loop()
                    logger.info(f"MongoDB operation loop id: {id(insert_loop)}")
                    logger.info(f"[MONGODB]\nCamera={camera_id}\nEVENT INSERT START")
                    await db.events.insert_one(event_doc)
                    logger.info(f"[MONGODB]\nCamera={camera_id}\nEVENT INSERT SUCCESS id={event_id}")
                except Exception as e:
                    import traceback
                    logger.error(f"[MONGODB]\nCamera={camera_id}\nEVENT INSERT FAILED error={e}\n{traceback.format_exc()}")
            else:
                logger.warning(f"[MONGODB]\nCamera={camera_id}\nEVENT INSERT FAILED error=MongoDB unconfigured/offline")

            # 2. Asynchronous background task for evidence capture & Telegram alerts (continues regardless of DB result)
            asyncio.create_task(
                self._process_evidence_and_telegram(
                    event_id=event_id,
                    camera_id=camera_id,
                    camera_name=camera_name or f"Camera {camera_id}",
                    roi_id=roi_id,
                    roi_name=roi_name or "ROI",
                    detection_source=detection_source,
                    confidence=confidence,
                    frame=frame.copy() if frame is not None else None,
                    width=width,
                    height=height,
                    fps=fps,
                    event_timestamp=event_timestamp,
                )
            )
            return True

        except Exception as e:
            import traceback
            logger.error(f"[EVENT SERVICE ERROR]\nCamera={camera_id}\nFAILED error={e}\n{traceback.format_exc()}")
            key = (str(camera_id), str(roi_id))
            if key in self.roi_states:
                self.roi_states[key]["is_occupied"] = False
            return False

    async def _process_evidence_and_telegram(
        self,
        event_id: ObjectId,
        camera_id: str,
        camera_name: str,
        roi_id: str,
        roi_name: str,
        detection_source: str,
        confidence: float,
        frame,
        width: int,
        height: int,
        fps: float,
        event_timestamp: datetime,
    ):
        """
        Background worker that captures snapshot, triggers Telegram alerts, and records 10s video.
        Guarantees that live stream processing is never blocked.
        """
        db = get_database()

        # Step A: Snapshot Capture & Update
        snapshot_url = None
        snapshot_path = None
        if frame is not None:
            logger.info(f"[SNAPSHOT]\nCamera={camera_id}\nSTART")
            logger.info(f"[SNAPSHOT]\nCamera={camera_id}\nframe.shape={frame.shape} frame.dtype={frame.dtype}")
            
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"intrusion_{camera_id}_{timestamp_str}.jpg"
            snapshot_path = os.path.join(self.snapshots_dir, filename)

            try:
                os.makedirs(self.snapshots_dir, exist_ok=True)
                success = cv2.imwrite(snapshot_path, frame)
                if success and os.path.exists(snapshot_path):
                    file_size = os.path.getsize(snapshot_path)
                    if file_size > 0:
                        snapshot_url = f"/storage/snapshots/{filename}"
                        logger.info(f"[SNAPSHOT]\nCamera={camera_id}\nSUCCESS path={snapshot_path} size={file_size} bytes")

                        if db is not None:
                            try:
                                await db.events.update_one(
                                    {"_id": event_id},
                                    {"$set": {"snapshot": snapshot_url}},
                                )
                            except Exception as db_err:
                                import traceback
                                logger.error(f"[MONGODB]\nCamera={camera_id}\nSNAPSHOT UPDATE FAILED error={db_err}\n{traceback.format_exc()}")
                    else:
                        logger.error(f"[SNAPSHOT]\nCamera={camera_id}\nFAILED error=0 byte snapshot file created at {snapshot_path}")
                else:
                    logger.error(f"[SNAPSHOT]\nCamera={camera_id}\nFAILED error=cv2.imwrite returned False for {snapshot_path}")
            except Exception as e:
                import traceback
                logger.error(f"[SNAPSHOT]\nCamera={camera_id}\nFAILED error={e}\n{traceback.format_exc()}")

        # Step B: Video Recording & Unified Telegram Alert Orchestration
        rec_started = False
        if frame is not None:
            try:
                logger.info(f"[RECORDING]\nCamera={camera_id}\nSTART")
                rec_path = self.recording_service.start_event_recording(
                    event_id=str(event_id),
                    camera_id=camera_id,
                    camera_name=camera_name,
                    roi_name=roi_name,
                    initial_frame=frame,
                    width=width,
                    height=height,
                    fps=fps,
                    duration=10.0,
                    detection_source=detection_source,
                    confidence=float(confidence),
                    event_timestamp=event_timestamp,
                    snapshot_path=snapshot_path,
                )
                if rec_path is not None:
                    rec_started = True
            except Exception as e:
                import traceback
                logger.error(f"[RECORDING]\nCamera={camera_id}\nFAILED error={e}\n{traceback.format_exc()}")

        # Step C: Fallback Telegram Alert (Only if recording failed to start)
        if not rec_started:
            try:
                logger.info(f"[TELEGRAM]\nCamera={camera_id}\nSEND FALLBACK UNIFIED ALERT (No Recording)")
                await self.telegram_service.send_intrusion_notification(
                    event_id=str(event_id),
                    camera_name=camera_name,
                    roi_name=roi_name,
                    detection_source=detection_source,
                    confidence=float(confidence),
                    timestamp=event_timestamp,
                    snapshot_path=snapshot_path,
                    video_path=None,
                )
            except Exception as e:
                import traceback
                logger.error(f"[TELEGRAM]\nCamera={camera_id}\nSEND FAILED error={e}\n{traceback.format_exc()}")



