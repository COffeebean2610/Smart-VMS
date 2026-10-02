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
logger = logging.getLogger("EvidencePipelineTest")

from app.db.database import connect_to_mongo, close_mongo_connection, get_database
from app.services.camera_service import CameraService, CameraStream
from app.services.frame_processor import FrameProcessor
from app.services.event_service import EventService
from app.services.recording_service import RecordingService

def create_synthetic_frame(color_rgb=(100, 100, 100), text="TEST FRAME"):
    frame = np.full((480, 640, 3), color_rgb, dtype=np.uint8)
    cv2.putText(frame, text, (40, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    return frame

class MockCameraStream(CameraStream):
    def __init__(self, camera_id: str, camera_name: str):
        super().__init__(camera_id, camera_name, "mock_url")
        self.is_running = True
        self.mock_frame = create_synthetic_frame((50, 50, 50), f"CAMERA {camera_id}")
        self.latest_raw_frame = self.mock_frame.copy()
        self.latest_frame_time = time.time()
        self.capture_fps = 30.0

    def set_mock_frame(self, frame):
        with self._lock:
            self.latest_raw_frame = frame.copy()
            self.latest_frame_time = time.time()
            self.frame_buffer.append(frame.copy())

async def run_evidence_pipeline_test():
    logger.info("==================================================")
    logger.info("POST-INTRUSION EVIDENCE PIPELINE VERIFICATION")
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

    cam1 = "CAM-EVIDENCE-001"
    cam2 = "CAM-EVIDENCE-002"

    if db is not None:
        await db.events.delete_many({"cameraId": {"$in": [cam1, cam2]}})
        await db.recordings.delete_many({"cameraId": {"$in": [cam1, cam2]}})

    stream1 = MockCameraStream(cam1, "Evidence Cam 1")
    stream2 = MockCameraStream(cam2, "Evidence Cam 2")

    camera_service = CameraService()
    camera_service.streams[cam1] = stream1
    camera_service.streams[cam2] = stream2

    ctx1 = frame_processor.get_context(cam1, "Evidence Cam 1")
    ctx1.rois = [{
        "id": "ROI-EV1",
        "name": "Zone EV1",
        "coordinates": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}, {"x": 0.1, "y": 0.9}],
        "cameraId": cam1
    }]

    ctx2 = frame_processor.get_context(cam2, "Evidence Cam 2")
    ctx2.rois = [{
        "id": "ROI-EV2",
        "name": "Zone EV2",
        "coordinates": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}, {"x": 0.1, "y": 0.9}],
        "cameraId": cam2
    }]

    test_results = {}

    # -------------------------------------------------------------
    # TEST 1: CAM-EVIDENCE-001 Intrusion Evidence Pipeline
    # -------------------------------------------------------------
    logger.info("\n--- [TEST 1] CAM-EVIDENCE-001 Post-Intrusion Evidence Pipeline ---")
    event_service.update_roi_absence(cam1, "ROI-EV1")

    frame1 = create_synthetic_frame((180, 40, 40), "INTRUSION CAM 1")
    stream1.set_mock_frame(frame1)

    frame_processor.process_camera_frame(stream1, "Evidence Cam 1")
    await asyncio.sleep(1.0) # Allow snapshot write & MongoDB insert

    evt1 = await db.events.find_one({"cameraId": cam1}) if db is not None else None
    test_results["TEST_1_EVENT_CAM1"] = evt1 is not None and evt1.get("cameraId") == cam1
    logger.info(f"TEST 1 (Event DB): PASS={test_results['TEST_1_EVENT_CAM1']} | Event ID: {evt1['_id'] if evt1 else 'None'}")

    snapshot_path_1 = None
    if evt1 and evt1.get("snapshot"):
        from app.core.paths import get_storage_dir
        snapshot_path_1 = os.path.join(str(get_storage_dir()), evt1["snapshot"].lstrip("/storage/"))

    test_results["TEST_1_SNAPSHOT_CAM1"] = snapshot_path_1 is not None and os.path.exists(snapshot_path_1) and os.path.getsize(snapshot_path_1) > 0
    logger.info(f"TEST 1 (Snapshot File): PASS={test_results['TEST_1_SNAPSHOT_CAM1']} | Path: {snapshot_path_1}")

    # -------------------------------------------------------------
    # TEST 2: CAM-EVIDENCE-002 Intrusion Evidence Pipeline
    # -------------------------------------------------------------
    logger.info("\n--- [TEST 2] CAM-EVIDENCE-002 Post-Intrusion Evidence Pipeline ---")
    event_service.update_roi_absence(cam2, "ROI-EV2")

    frame2 = create_synthetic_frame((40, 180, 40), "INTRUSION CAM 2")
    stream2.set_mock_frame(frame2)

    frame_processor.process_camera_frame(stream2, "Evidence Cam 2")
    await asyncio.sleep(1.0)

    evt2 = await db.events.find_one({"cameraId": cam2}) if db is not None else None
    test_results["TEST_2_EVENT_CAM2"] = evt2 is not None and evt2.get("cameraId") == cam2
    logger.info(f"TEST 2 (Event DB): PASS={test_results['TEST_2_EVENT_CAM2']} | Event ID: {evt2['_id'] if evt2 else 'None'}")

    snapshot_path_2 = None
    if evt2 and evt2.get("snapshot"):
        from app.core.paths import get_storage_dir
        snapshot_path_2 = os.path.join(str(get_storage_dir()), evt2["snapshot"].lstrip("/storage/"))

    test_results["TEST_2_SNAPSHOT_CAM2"] = snapshot_path_2 is not None and os.path.exists(snapshot_path_2) and os.path.getsize(snapshot_path_2) > 0
    logger.info(f"TEST 2 (Snapshot File): PASS={test_results['TEST_2_SNAPSHOT_CAM2']} | Path: {snapshot_path_2}")

    # -------------------------------------------------------------
    # TEST 3: Simultaneous Intrusions on CAM1 and CAM2
    # -------------------------------------------------------------
    logger.info("\n--- [TEST 3] Simultaneous Intrusions on CAM1 and CAM2 ---")
    if db is not None:
        await db.events.delete_many({"cameraId": {"$in": [cam1, cam2]}})

    event_service.update_roi_absence(cam1, "ROI-EV1")
    event_service.update_roi_absence(cam2, "ROI-EV2")

    stream1.set_mock_frame(create_synthetic_frame((220, 0, 0), "DUAL CAM 1"))
    stream2.set_mock_frame(create_synthetic_frame((0, 220, 0), "DUAL CAM 2"))

    frame_processor.process_camera_frame(stream1, "Evidence Cam 1")
    frame_processor.process_camera_frame(stream2, "Evidence Cam 2")
    await asyncio.sleep(1.0)

    evt3_c1 = await db.events.find_one({"cameraId": cam1}) if db is not None else None
    evt3_c2 = await db.events.find_one({"cameraId": cam2}) if db is not None else None

    test_results["TEST_3_SIMULTANEOUS_EVIDENCE"] = evt3_c1 is not None and evt3_c2 is not None and evt3_c1.get("cameraId") == cam1 and evt3_c2.get("cameraId") == cam2
    logger.info(f"TEST 3 Result: PASS={test_results['TEST_3_SIMULTANEOUS_EVIDENCE']} | CAM1 Event: {bool(evt3_c1)}, CAM2 Event: {bool(evt3_c2)}")

    # Cleanup DB records
    if db is not None:
        await db.events.delete_many({"cameraId": {"$in": [cam1, cam2]}})
        await db.recordings.delete_many({"cameraId": {"$in": [cam1, cam2]}})

    await close_mongo_connection()

    logger.info("\n==================================================")
    logger.info("POST-INTRUSION EVIDENCE PIPELINE VERIFICATION SUMMARY")
    logger.info("==================================================")
    all_passed = all(test_results.values())
    for name, res in test_results.items():
        logger.info(f" - {name:35s}: {'PASS' if res else 'FAIL'}")

    logger.info(f"\nOVERALL RESULT: {'ALL EVIDENCE PIPELINE TESTS PASSED 100%' if all_passed else 'SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_evidence_pipeline_test())
