import asyncio
import logging
import os
import sys
import time
import numpy as np
import cv2
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WebSocketStreamTest")

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.database import connect_to_mongo, close_mongo_connection, get_database
from app.services.camera_service import CameraService, CameraStream
from app.services.frame_processor import FrameProcessor
from app.services.event_service import EventService
from app.services.recording_service import RecordingService

def create_synthetic_frame(color_rgb, text=""):
    frame = np.full((480, 640, 3), color_rgb, dtype=np.uint8)
    if text:
        cv2.putText(frame, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    return frame

class MockCameraStream(CameraStream):
    def __init__(self, camera_id: str, camera_name: str):
        super().__init__(camera_id, camera_name, "mock_url")
        self.is_running = True
        self.mock_frame = create_synthetic_frame((80, 80, 80), f"CAM {camera_id}")
        self.latest_raw_frame = self.mock_frame.copy()
        self.latest_frame_time = time.time()
        self.capture_fps = 30.0

    def start(self):
        self.is_running = True

    def set_mock_frame(self, frame):
        with self._lock:
            self.latest_raw_frame = frame.copy()
            self.latest_frame_time = time.time()
            self.frame_buffer.append(frame.copy())

async def run_websocket_tests():
    logger.info("==================================================")
    logger.info("WEBSOCKET LIVE VIEW & EVIDENCE PIPELINE VERIFICATION")
    logger.info("==================================================")

    # Setup database and event loop
    loop = asyncio.get_running_loop()
    connected = await connect_to_mongo()
    db = get_database()

    frame_processor = FrameProcessor()
    frame_processor.set_main_event_loop(loop)

    recording_service = RecordingService()
    recording_service.set_event_loop(loop)

    # Set up mock streams
    cam1 = "CAM-WS-001"
    cam2 = "CAM-WS-002"

    if db is not None:
        await db.events.delete_many({"cameraId": {"$in": [cam1, cam2]}})
        await db.recordings.delete_many({"cameraId": {"$in": [cam1, cam2]}})

    stream1 = MockCameraStream(cam1, "WebSocket Cam 1")
    stream2 = MockCameraStream(cam2, "WebSocket Cam 2")

    camera_service = CameraService()
    camera_service.streams[cam1] = stream1
    camera_service.streams[cam2] = stream2

    ctx1 = frame_processor.get_context(cam1, "WebSocket Cam 1")
    ctx1.rois = [{
        "id": "ROI-WS1",
        "name": "Zone WS1",
        "coordinates": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}, {"x": 0.1, "y": 0.9}],
        "cameraId": cam1
    }]

    ctx2 = frame_processor.get_context(cam2, "WebSocket Cam 2")
    ctx2.rois = [{
        "id": "ROI-WS2",
        "name": "Zone WS2",
        "coordinates": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}, {"x": 0.1, "y": 0.9}],
        "cameraId": cam2
    }]

    # Process initial frames to encode JPEGs into contexts
    frame_processor.process_camera_frame(stream1, "WebSocket Cam 1")
    frame_processor.process_camera_frame(stream2, "WebSocket Cam 2")

    test_results = {}

    # TEST 1: Verify JPEG bytes generated in CameraProcessorContext
    test_results["TEST_1_JPEG_GENERATION"] = ctx1.latest_jpeg_bytes is not None and len(ctx1.latest_jpeg_bytes) > 500
    logger.info(f"TEST 1 Result: PASS={test_results['TEST_1_JPEG_GENERATION']} | JPEG Size: {len(ctx1.latest_jpeg_bytes) if ctx1.latest_jpeg_bytes else 0} bytes")

    # TEST 2: Verify Rolling Frame Buffer for Pre-Intrusion Video Clips
    buf_len = len(stream1.get_pre_buffer())
    test_results["TEST_2_PRE_BUFFER"] = buf_len > 0
    logger.info(f"TEST 2 Result: PASS={test_results['TEST_2_PRE_BUFFER']} | Rolling Buffer Count: {buf_len} frames")

    # TEST 3: Intrusion Evidence Generation on CAM1
    event_service = EventService()
    event_service.update_roi_absence(cam1, "ROI-WS1")

    intrusion_frame1 = create_synthetic_frame((200, 0, 0), "WS-001 INTRUSION")
    stream1.set_mock_frame(intrusion_frame1)
    frame_processor.process_camera_frame(stream1, "WebSocket Cam 1")
    await asyncio.sleep(0.5)

    evt1 = await db.events.find_one({"cameraId": cam1}) if db is not None else None
    test_results["TEST_3_EVIDENCE_CAM1"] = evt1 is not None and evt1.get("cameraId") == cam1
    logger.info(f"TEST 3 Result: PASS={test_results['TEST_3_EVIDENCE_CAM1']} | Event ID: {evt1['_id'] if evt1 else 'None'}")

    # TEST 4: Intrusion Evidence Generation on CAM2
    event_service.update_roi_absence(cam2, "ROI-WS2")

    intrusion_frame2 = create_synthetic_frame((0, 200, 0), "WS-002 INTRUSION")
    stream2.set_mock_frame(intrusion_frame2)
    frame_processor.process_camera_frame(stream2, "WebSocket Cam 2")
    await asyncio.sleep(0.5)

    evt2 = await db.events.find_one({"cameraId": cam2}) if db is not None else None
    test_results["TEST_4_EVIDENCE_CAM2"] = evt2 is not None and evt2.get("cameraId") == cam2
    logger.info(f"TEST 4 Result: PASS={test_results['TEST_4_EVIDENCE_CAM2']} | Event ID: {evt2['_id'] if evt2 else 'None'}")

    # Cleanup DB records
    if db is not None:
        await db.events.delete_many({"cameraId": {"$in": [cam1, cam2]}})
        await db.recordings.delete_many({"cameraId": {"$in": [cam1, cam2]}})

    await close_mongo_connection()

    logger.info("\n==================================================")
    logger.info("TEST SUITE SUMMARY")
    logger.info("==================================================")
    all_passed = all(test_results.values())
    for name, res in test_results.items():
        logger.info(f" - {name:30s}: {'PASS' if res else 'FAIL'}")

    logger.info(f"\nOVERALL RESULT: {'ALL VERIFICATIONS PASSED 100%' if all_passed else 'SOME VERIFICATIONS FAILED'}")
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_websocket_tests())
