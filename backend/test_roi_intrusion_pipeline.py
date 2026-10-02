import asyncio
import logging
import os
import sys
import time
import numpy as np
import cv2

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RoiPipelineTest")

from app.db.database import connect_to_mongo, close_mongo_connection, get_database
from app.services.camera_service import CameraService, CameraStream
from app.services.frame_processor import FrameProcessor
from app.services.event_service import EventService
from app.services.recording_service import RecordingService
from app.services.roi_service import RoiService

def create_person_synthetic_frame(w=640, h=480, bbox=[100, 100, 300, 400]):
    """Creates a synthetic frame (640x480)."""
    frame = np.full((h, w, 3), (40, 40, 40), dtype=np.uint8)
    x1, y1, x2, y2 = bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), -1)
    cv2.putText(frame, "PERSON SIM", (x1 + 10, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return frame

class MockCameraStream(CameraStream):
    def __init__(self, camera_id: str, camera_name: str):
        super().__init__(camera_id, camera_name, "mock_url")
        self.is_running = True
        self.latest_raw_frame = create_person_synthetic_frame()
        self.latest_frame_time = time.time()
        self.capture_fps = 30.0

    def set_mock_frame(self, frame):
        with self._lock:
            self.latest_raw_frame = frame.copy()
            self.latest_frame_time = time.time()
            self.frame_buffer.append(frame.copy())

async def run_roi_pipeline_test():
    logger.info("==================================================")
    logger.info("TESTING ROI INTRUSION & EVIDENCE PIPELINE VERIFICATION")
    logger.info("==================================================")

    # 1. Main loop & MongoDB setup
    loop = asyncio.get_running_loop()
    connected = await connect_to_mongo()
    db = get_database()

    frame_processor = FrameProcessor()
    frame_processor.set_main_event_loop(loop)

    recording_service = RecordingService()
    recording_service.set_event_loop(loop)

    event_service = EventService()

    cam_id_1 = "CAM-ROI-001"
    cam_id_2 = "CAM-ROI-002"

    if db is not None:
        await db.events.delete_many({"cameraId": {"$in": [cam_id_1, cam_id_2]}})
        await db.recordings.delete_many({"cameraId": {"$in": [cam_id_1, cam_id_2]}})
        await db.detection_zones.delete_many({"cameraId": {"$in": [cam_id_1, cam_id_2]}})

        # Seed ROI into MongoDB
        await db.detection_zones.insert_one({
            "zoneName": "Restricted Zone CAM1",
            "cameraId": cam_id_1,
            "coordinates": [{"x": 0.05, "y": 0.05}, {"x": 0.95, "y": 0.05}, {"x": 0.95, "y": 0.95}, {"x": 0.05, "y": 0.95}],
            "createdAt": time.time()
        })
        await db.detection_zones.insert_one({
            "zoneName": "Restricted Zone CAM2",
            "cameraId": cam_id_2,
            "coordinates": [{"x": 0.05, "y": 0.05}, {"x": 0.95, "y": 0.05}, {"x": 0.95, "y": 0.95}, {"x": 0.05, "y": 0.95}],
            "createdAt": time.time()
        })

    # Test update_rois loads DB ROIs into processor contexts
    await frame_processor.update_rois()

    ctx1 = frame_processor.get_context(cam_id_1, "ROI Camera 1")
    ctx2 = frame_processor.get_context(cam_id_2, "ROI Camera 2")

    test_results = {}
    test_results["TEST_1_ROI_LOADING"] = len(ctx1.rois) > 0 and len(ctx2.rois) > 0
    logger.info(f"TEST 1 Result (ROI DB Loading): PASS={test_results['TEST_1_ROI_LOADING']} | CAM1 ROIs={len(ctx1.rois)}, CAM2 ROIs={len(ctx2.rois)}")

    stream1 = MockCameraStream(cam_id_1, "ROI Camera 1")
    stream2 = MockCameraStream(cam_id_2, "ROI Camera 2")

    camera_service = CameraService()
    camera_service.streams[cam_id_1] = stream1
    camera_service.streams[cam_id_2] = stream2

    event_service.update_roi_absence(cam_id_1, ctx1.rois[0]["id"])

    # 2. Test check_intrusion algorithm directly
    bbox_test = [100, 100, 300, 400] # Inside [0.05, 0.05] -> [0.95, 0.95] normalized ROI
    inside_calc, (cx, cy), _ = RoiService.check_intrusion(bbox_test, 640, 480, ctx1.rois[0]["coordinates"])
    test_results["TEST_2_CHECK_INTRUSION_CALC"] = inside_calc
    logger.info(f"TEST 2 Result (check_intrusion Calc): PASS={inside_calc} | Point=({cx},{cy})")

    # 3. Simulate Person Frame Processing for CAM-ROI-001
    person_frame = create_person_synthetic_frame()
    stream1.set_mock_frame(person_frame)

    # Mock YOLO result by injecting det directly or letting YOLO process
    frame_processor.process_camera_frame(stream1, "ROI Camera 1")
    await asyncio.sleep(1.0) # Allow async task to complete snapshot & MongoDB write

    # Verify Event in MongoDB
    evt1 = await db.events.find_one({"cameraId": cam_id_1}) if db is not None else None
    test_results["TEST_3_EVENT_DISPATCH"] = evt1 is not None and evt1.get("cameraId") == cam_id_1
    logger.info(f"TEST 3 Result (MongoDB Event Created): PASS={test_results['TEST_3_EVENT_DISPATCH']} | Event ID: {evt1['_id'] if evt1 else 'None'}")

    # Verify Snapshot on Disk
    snapshot_path = None
    if evt1 and evt1.get("snapshot"):
        snapshot_rel = evt1["snapshot"]
        from app.core.paths import get_storage_dir
        snapshot_path = os.path.join(str(get_storage_dir()), snapshot_rel.lstrip("/storage/"))
    
    test_results["TEST_4_SNAPSHOT_EXISTS"] = snapshot_path is not None and os.path.exists(snapshot_path) and os.path.getsize(snapshot_path) > 0
    logger.info(f"TEST 4 Result (Snapshot Created on Disk): PASS={test_results['TEST_4_SNAPSHOT_EXISTS']} | Path: {snapshot_path}")

    # Clean up DB
    if db is not None:
        await db.events.delete_many({"cameraId": {"$in": [cam_id_1, cam_id_2]}})
        await db.recordings.delete_many({"cameraId": {"$in": [cam_id_1, cam_id_2]}})
        await db.detection_zones.delete_many({"cameraId": {"$in": [cam_id_1, cam_id_2]}})

    await close_mongo_connection()

    logger.info("\n==================================================")
    logger.info("ROI PIPELINE VERIFICATION SUMMARY")
    logger.info("==================================================")
    all_passed = all(test_results.values())
    for name, res in test_results.items():
        logger.info(f" - {name:35s}: {'PASS' if res else 'FAIL'}")

    logger.info(f"\nOVERALL RESULT: {'ALL ROI PIPELINE VERIFICATIONS PASSED 100%' if all_passed else 'SOME VERIFICATIONS FAILED'}")
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_roi_pipeline_test())
