import asyncio
import logging
import os
import sys
import time

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MongoEventLoopTest")

from app.db.database import connect_to_mongo, close_mongo_connection, get_database
from app.services.frame_processor import FrameProcessor
from app.services.event_service import EventService
from app.services.recording_service import RecordingService
from app.services.camera_service import CameraService, CameraStream
import numpy as np

class DummyStream(CameraStream):
    def __init__(self, camera_id, camera_name):
        super().__init__(camera_id, camera_name, "mock")
        self.is_running = True
        self.latest_raw_frame = np.full((480, 640, 3), 128, dtype=np.uint8)
        self.latest_frame_time = time.time()
        self.capture_fps = 30.0

async def verify_mongo_event_loop():
    logger.info("==================================================")
    logger.info("TESTING MONGODB ASYNCIO EVENT LOOP INTEGRATION")
    logger.info("==================================================")

    # 1. Main Loop Setup
    main_loop = asyncio.get_running_loop()
    main_loop_id = id(main_loop)
    logger.info(f"[TEST MAIN] Main FastAPI event loop id: {main_loop_id}")

    # Set up services
    frame_processor = FrameProcessor()
    frame_processor.set_main_event_loop(main_loop)
    recording_service = RecordingService()
    recording_service.set_event_loop(main_loop)

    # 2. Connect to MongoDB Atlas
    connected = await connect_to_mongo()
    if not connected:
        logger.error("[TEST ERROR] Could not connect to MongoDB Atlas.")
        return False

    db = get_database()
    if db is None:
        logger.error("[TEST ERROR] Database instance is None.")
        return False

    # 3. Register Test Cameras & ROIs
    cam_id_1 = "CAM-LOOP-001"
    cam_id_2 = "CAM-LOOP-002"

    await db.events.delete_many({"cameraId": {"$in": [cam_id_1, cam_id_2]}})

    stream1 = DummyStream(cam_id_1, "Loop Cam 1")
    stream2 = DummyStream(cam_id_2, "Loop Cam 2")

    camera_service = CameraService()
    camera_service.streams[cam_id_1] = stream1
    camera_service.streams[cam_id_2] = stream2

    ctx1 = frame_processor.get_context(cam_id_1, "Loop Cam 1")
    ctx1.rois = [{
        "id": "ROI-L1",
        "name": "Zone L1",
        "coordinates": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}, {"x": 0.1, "y": 0.9}],
        "cameraId": cam_id_1
    }]

    ctx2 = frame_processor.get_context(cam_id_2, "Loop Cam 2")
    ctx2.rois = [{
        "id": "ROI-L2",
        "name": "Zone L2",
        "coordinates": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}, {"x": 0.1, "y": 0.9}],
        "cameraId": cam_id_2
    }]

    event_service = EventService()
    event_service.update_roi_absence(cam_id_1, "ROI-L1")
    event_service.update_roi_absence(cam_id_2, "ROI-L2")

    # 4. Trigger Intrusions from Background Thread Context (mimicking process_camera_frame)
    logger.info("\n--- [TEST] Triggering intrusion on CAM-LOOP-001 ---")
    frame1 = np.full((480, 640, 3), 200, dtype=np.uint8)
    stream1.latest_raw_frame = frame1

    frame_processor.process_camera_frame(stream1, "Loop Cam 1")
    await asyncio.sleep(0.5)

    # Verify document in MongoDB Atlas
    doc1 = await db.events.find_one({"cameraId": cam_id_1})
    if doc1 and doc1.get("cameraId") == cam_id_1:
        logger.info(f"SUCCESS: CAM-LOOP-001 event created in MongoDB Atlas: {doc1['_id']}")
    else:
        logger.error("FAILURE: CAM-LOOP-001 event NOT found in MongoDB Atlas.")
        return False

    logger.info("\n--- [TEST] Triggering intrusion on CAM-LOOP-002 ---")
    frame2 = np.full((480, 640, 3), 220, dtype=np.uint8)
    stream2.latest_raw_frame = frame2

    frame_processor.process_camera_frame(stream2, "Loop Cam 2")
    await asyncio.sleep(0.5)

    doc2 = await db.events.find_one({"cameraId": cam_id_2})
    if doc2 and doc2.get("cameraId") == cam_id_2:
        logger.info(f"SUCCESS: CAM-LOOP-002 event created in MongoDB Atlas: {doc2['_id']}")
    else:
        logger.error("FAILURE: CAM-LOOP-002 event NOT found in MongoDB Atlas.")
        return False

    # Cleanup test records
    await db.events.delete_many({"cameraId": {"$in": [cam_id_1, cam_id_2]}})
    await close_mongo_connection()

    logger.info("\n==================================================")
    logger.info("MONGODB ASYNCIO EVENT LOOP INTEGRATION PASSED 100%")
    logger.info("==================================================")
    return True

if __name__ == "__main__":
    success = asyncio.run(verify_mongo_event_loop())
    sys.exit(0 if success else 1)
