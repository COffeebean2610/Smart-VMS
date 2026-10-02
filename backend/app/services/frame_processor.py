import asyncio
import logging
import threading
import time
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from app.db.database import get_database
from app.services.camera_service import CameraService, CameraStream
from app.services.event_service import EventService
from app.services.recording_service import RecordingService
from app.services.roi_service import RoiService
from app.services.yolo_service import YoloService

logger = logging.getLogger(__name__)


class CameraProcessorContext:
    """
    Maintains detection state, ROI processing, JPEG encoding, and metrics for one camera.
    """
    def __init__(self, camera_id: str, camera_name: str):
        self.camera_id = str(camera_id)
        self.camera_name = str(camera_name)
        self.rois: List[Dict[str, Any]] = []
        self.prev_gray_rois: Dict[str, Any] = {}
        self.latest_jpeg_bytes: Optional[bytes] = None
        self.latest_debug_status: Dict[str, Any] = {}
        
        # Real-time Metrics
        self.detection_fps: float = 0.0
        self.frame_age_ms: float = 0.0
        self.inference_time_ms: float = 0.0
        self.detections_count: int = 0
        self.frames_processed: int = 0
        self.last_fps_calc: float = time.time()
        self._lock = threading.Lock()


class FrameProcessor:
    camera_service: CameraService
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FrameProcessor, cls).__new__(cls)
            cls._instance.camera_service = CameraService()
            cls._instance.yolo_service = YoloService()
            cls._instance.event_service = EventService()
            cls._instance.recording_service = RecordingService()
            cls._instance.contexts: Dict[str, CameraProcessorContext] = {}
            cls._instance.yolo_lock = threading.Lock()
            cls._instance.conf_threshold = 0.50
            cls._instance.motion_threshold = 0.02
            cls._instance.min_motion_area = 300
            cls._instance.is_running = True
            cls._instance._background_task = None
            cls._instance.main_event_loop = None
            cls._instance.start_background_processing()
        return cls._instance

    def set_main_event_loop(self, loop: asyncio.AbstractEventLoop):
        self.main_event_loop = loop
        logger.info(f"[FRAME PROCESSOR] Main event loop set: {loop}")

    def start_background_processing(self):
        if self._background_task is None or not self._background_task.is_alive():
            self.is_running = True
            self._background_task = threading.Thread(target=self._background_loop, daemon=True)
            self._background_task.start()

    def _background_loop(self):
        logger.info("[FRAME PROCESSOR] Background multi-camera detection loop started.")
        while self.is_running:
            try:
                streams = list(self.camera_service.streams.values())
                if not streams and self.camera_service.active_camera_id:
                    # Auto-initialize primary stream
                    self.camera_service.get_or_create_stream(
                        self.camera_service.active_camera_id, "Primary Camera", 0
                    )
                    streams = list(self.camera_service.streams.values())

                for stream in streams:
                    if stream.is_running:
                        self.process_camera_frame(stream, stream.camera_name)
            except Exception as e:
                logger.error(f"[FRAME PROCESSOR ERROR] Background loop error: {e}")
            time.sleep(0.033)

    def get_context(self, camera_id: str, camera_name: str = "Camera") -> CameraProcessorContext:
        camera_id = str(camera_id)
        if camera_id not in self.contexts:
            self.contexts[camera_id] = CameraProcessorContext(camera_id, camera_name)
        else:
            self.contexts[camera_id].camera_name = camera_name
        return self.contexts[camera_id]

    async def update_rois(self):
        """
        Refreshes ROIs from MongoDB and maps them to their respective camera_id.
        """
        try:
            db = get_database()
            if db is None:
                return
            cursor = db.detection_zones.find({})
            rois_by_cam: Dict[str, List[Dict[str, Any]]] = {}
            total_loaded = 0
            
            async for roi in cursor:
                cam_id = str(roi.get("cameraId", "default_cam_01"))
                if cam_id not in rois_by_cam:
                    rois_by_cam[cam_id] = []
                rois_by_cam[cam_id].append(
                    {
                        "id": str(roi["_id"]),
                        "name": roi.get("zoneName", "Zone"),
                        "coordinates": roi.get("coordinates", []),
                        "cameraId": cam_id,
                    }
                )
                total_loaded += 1

            # Update contexts
            for cam_id, rois in rois_by_cam.items():
                ctx = self.get_context(cam_id)
                ctx.rois = rois
                
            # For contexts with no DB ROIs
            for cam_id, ctx in self.contexts.items():
                if cam_id not in rois_by_cam:
                    ctx.rois = []
                    
            logger.info(f"[FRAME PROCESSOR] Loaded {total_loaded} ROI(s) across {len(rois_by_cam)} camera(s) from MongoDB.")
        except Exception as e:
            logger.error(f"Error updating ROIs in FrameProcessor: {e}")

    def process_camera_frame(self, stream: CameraStream, camera_name: str):
        """
        Processes the latest raw frame for one camera (Low-Latency Strategy).
        """
        raw_frame, frame_time, frame_age_ms = stream.get_latest_raw_frame()
        if raw_frame is None:
            return

        ctx = self.get_context(stream.camera_id, camera_name)
        ctx.frame_age_ms = frame_age_ms

        h, w = raw_frame.shape[:2]
        clean_frame = raw_frame.copy()
        display_frame = np.ascontiguousarray(raw_frame.copy())

        # Write clean frame to event video recorders
        self.recording_service.write_frame(stream.camera_id, clean_frame)

        # 1. Thread-safe YOLO Inference
        t0 = time.time()
        with self.yolo_lock:
            detections = self.yolo_service.detect_persons(
                clean_frame, conf_threshold=self.conf_threshold
            )
        inference_time = round((time.time() - t0) * 1000, 1)
        ctx.inference_time_ms = inference_time
        ctx.detections_count = len(detections)

        active_rois = ctx.rois

        if len(detections) > 0 and len(active_rois) > 0:
            logger.info(f"[{stream.camera_id}] PERSON DETECTED: count={len(detections)} | Active ROIs={len(active_rois)}")

        # 2. Process Camera-Specific ROIs
        for roi in active_rois:
            roi_id = roi["id"]
            roi_name = roi["name"]
            coords = roi["coordinates"]

            if len(coords) < 2:
                continue

            min_x, min_y, max_x, max_y = RoiService.get_roi_bounds(coords, w, h)
            roi_w = max_x - min_x
            roi_h = max_y - min_y

            if roi_w <= 0 or roi_h <= 0:
                continue

            # Throttled ~1s per-frame diagnostic logging per camera/ROI
            now_ts = time.time()
            debug_key = f"{stream.camera_id}_{roi_id}"
            if now_ts - getattr(self, "last_roi_debug_log", {}).get(debug_key, 0.0) >= 1.0:
                if not hasattr(self, "last_roi_debug_log"):
                    self.last_roi_debug_log = {}
                self.last_roi_debug_log[debug_key] = now_ts
                
                roi_cam = roi.get("cameraId", stream.camera_id)
                cam_match = str(roi_cam) == str(stream.camera_id) or roi_cam in ("default_cam_01", stream.camera_id)
                logger.info(f"[ROI STATE]\ncamera_id={stream.camera_id}\nroi_id={roi_id}\nenabled=true\ncamera_match={cam_match}")

                for det in detections:
                    p_bbox = det["bbox"]
                    p_conf = det["confidence"]
                    inside_check, (cx, cy), (foot_in, center_in, box_ov) = RoiService.check_intrusion(p_bbox, w, h, coords)
                    p_foot = (cx, p_bbox[3])
                    logger.info(
                        f"[ROI DEBUG]\n"
                        f"camera_id={stream.camera_id}\n"
                        f"roi_id={roi_id}\n"
                        f"roi_bounds=({min_x},{min_y},{max_x},{max_y})\n"
                        f"frame_size={w}x{h}\n"
                        f"person_bbox={p_bbox}\n"
                        f"person_confidence={p_conf:.2f}\n"
                        f"person_foot_point={p_foot}\n"
                        f"person_center=({cx},{cy})\n"
                        f"foot_inside={foot_in}\n"
                        f"center_inside={center_in}\n"
                        f"intersection={box_ov}\n"
                        f"intrusion_detected={inside_check}"
                    )

            # OpenCV Motion Check inside ROI
            prev_gray = ctx.prev_gray_rois.get(roi_id)
            motion_detected, motion_ratio, current_gray_roi = RoiService.detect_motion_in_roi(
                clean_frame,
                prev_gray,
                min_x,
                min_y,
                max_x,
                max_y,
                motion_threshold=self.motion_threshold,
                min_motion_area=self.min_motion_area,
            )
            ctx.prev_gray_rois[roi_id] = current_gray_roi

            # YOLO Person Check inside ROI
            person_inside_roi = False
            person_conf = 0.0
            person_bbox = None

            for det in detections:
                inside, (cx, cy), (foot_in, center_in, box_ov) = RoiService.check_intrusion(det["bbox"], w, h, coords)
                if inside:
                    person_inside_roi = True
                    person_conf = max(person_conf, det["confidence"])
                    person_bbox = det["bbox"]

            intrusion_detected = person_inside_roi or motion_detected

            if person_inside_roi and motion_detected:
                detection_source = "person+motion"
            elif person_inside_roi:
                detection_source = "person"
            elif motion_detected:
                detection_source = "motion"
            else:
                detection_source = "none"

            ctx.latest_debug_status[roi_id] = {
                "cameraId": stream.camera_id,
                "roiId": roi_id,
                "roiName": roi_name,
                "motionDetected": bool(motion_detected),
                "motionRatio": float(motion_ratio),
                "personDetected": bool(len(detections) > 0),
                "personInsideROI": bool(person_inside_roi),
                "intrusionDetected": bool(intrusion_detected),
                "detectionSource": detection_source,
            }

            logger.info(
                f"[INTRUSION CONDITION]\n"
                f"camera={stream.camera_id}\n"
                f"roi={roi_id}\n"
                f"person_detected={len(detections) > 0}\n"
                f"person_inside_roi={person_inside_roi}\n"
                f"motion_detected={motion_detected}\n"
                f"intrusion_detected={intrusion_detected}"
            )

            # State Machine & Event Dispatch
            if intrusion_detected:
                confidence_val = person_conf if person_inside_roi else min(1.0, motion_ratio * 10.0)
                logger.info(f"[INTRUSION TRUE]\ncamera={stream.camera_id}\nroi={roi_id}")
                logger.info(f"[INTRUSION]\nCamera={stream.camera_id}\nROI={roi_id}\nconfidence={confidence_val:.2f}")
                logger.info(f"[EVENT DISPATCHING]\nCamera={stream.camera_id}\nROI={roi_id}\nframe_available={clean_frame is not None}")

                coro = self.event_service.handle_intrusion(
                    camera_id=stream.camera_id,
                    camera_name=camera_name,
                    roi_id=roi_id,
                    roi_name=roi_name,
                    detection_source=detection_source,
                    bbox=person_bbox or [min_x, min_y, max_x, max_y],
                    confidence=confidence_val,
                    frame=clean_frame,
                    width=w,
                    height=h,
                    fps=20.0,
                )
                if self.main_event_loop and self.main_event_loop.is_running():
                    asyncio.run_coroutine_threadsafe(coro, self.main_event_loop)
                else:
                    logger.warning(f"[{stream.camera_id}] Main event loop not running. Delayed intrusion dispatch for ROI {roi_name}.")
            else:
                self.event_service.update_roi_absence(stream.camera_id, roi_id)

            # Visual Debug Overlays
            box_color = (0, 0, 255) if intrusion_detected else (0, 255, 0)
            box_thickness = 3 if intrusion_detected else 2

            cv2.rectangle(display_frame, (min_x, min_y), (max_x, max_y), box_color, box_thickness)
            status_text = f"ALERT: {roi_name}" if intrusion_detected else roi_name
            cv2.putText(
                display_frame,
                status_text,
                (max(10, min_x), max(20, min_y - 30)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                box_color,
                2,
            )

            motion_str = f"Motion: {'YES' if motion_detected else 'NO'} ({motion_ratio*100:.1f}%)"
            person_str = f"Person: {'YES' if person_inside_roi else 'NO'} ({int(person_conf*100)}%)"

            cv2.putText(
                display_frame,
                motion_str,
                (max(10, min_x), max(35, min_y - 16)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 255) if motion_detected else (0, 255, 0),
                1,
            )
            cv2.putText(
                display_frame,
                person_str,
                (max(10, min_x), max(50, min_y - 2)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 255) if person_inside_roi else (0, 255, 0),
                1,
            )

        # 3. Draw Bounding Boxes for Persons
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf = det["confidence"]
            cx, cy = int((x1 + x2) / 2.0), int((y1 + y2) / 2.0)

            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(
                display_frame,
                f"Person {conf:.2f}",
                (x1, max(15, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 0),
                2,
            )
            cv2.circle(display_frame, (cx, cy), 5, (0, 255, 255), -1)

        # Encode JPEG for MJPEG stream with robust error handling
        try:
            ret, buffer = cv2.imencode(".jpg", display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ret and buffer is not None:
                jpeg_bytes = buffer.tobytes()
                with ctx._lock:
                    ctx.latest_jpeg_bytes = jpeg_bytes
                    ctx.frames_processed += 1

                    # Calculate Detection FPS
                    now = time.time()
                    elapsed = now - ctx.last_fps_calc
                    if elapsed >= 1.0:
                        ctx.detection_fps = round(ctx.frames_processed / elapsed, 1)
                        ctx.frames_processed = 0
                        ctx.last_fps_calc = now
        except Exception as e:
            logger.error(f"[FRAME PROCESSOR ERROR] JPEG encoding failed for camera {stream.camera_id}: {e}")

    async def generate_frames(self, camera_id: Optional[str] = None):
        """
        Instant low-latency MJPEG stream generator. Reads latest pre-processed JPEG bytes without blocking.
        """
        await self.update_rois()
        
        if not camera_id:
            camera_id = self.camera_service.active_camera_id

        camera_id = str(camera_id)

        while True:
            stream = self.camera_service.get_stream(camera_id)
            
            # Ensure stream exists
            if not stream and camera_id in ("default_cam_01", self.camera_service.active_camera_id):
                stream = self.camera_service.get_or_create_stream(camera_id, "Primary Camera", 0)

            if stream:
                ctx = self.get_context(camera_id, stream.camera_name)
                with ctx._lock:
                    frame_bytes = ctx.latest_jpeg_bytes

                if frame_bytes:
                    header = (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(frame_bytes)).encode() + b"\r\n\r\n"
                    )
                    yield (header + frame_bytes + b"\r\n")

            await asyncio.sleep(0.033)  # ~30 FPS stream delivery rate


    def get_metrics(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns real-time performance diagnostic metrics for all cameras or a specific camera.
        """
        metrics = {}
        now = time.time()
        cam_ids = set(self.camera_service.streams.keys()).union(set(self.contexts.keys()))
        if not cam_ids and self.camera_service.active_camera_id:
            cam_ids.add(self.camera_service.active_camera_id)

        for cam_id in cam_ids:
            stream = self.camera_service.get_stream(cam_id)
            ctx = self.get_context(cam_id, stream.camera_name if stream else "Camera")
            
            # Compute detection FPS dynamically
            elapsed = now - ctx.last_fps_calc
            if elapsed >= 1.0:
                ctx.detection_fps = round(ctx.frames_processed / elapsed, 1)
                ctx.frames_processed = 0
                ctx.last_fps_calc = now

            status_str = "online" if (stream and stream.is_running and stream.latest_raw_frame is not None) else ("camera_blocked" if (stream and stream.error_reason == "camera_blocked") else "offline")

            metrics[cam_id] = {
                "cameraId": cam_id,
                "cameraName": stream.camera_name if stream else ctx.camera_name,
                "captureFps": stream.capture_fps if stream else 0.0,
                "detectionFps": ctx.detection_fps,
                "frameAgeMs": ctx.frame_age_ms,
                "inferenceTimeMs": ctx.inference_time_ms,
                "detectionsCount": ctx.detections_count,
                "activeRoisCount": len(ctx.rois),
                "status": status_str,
                "errorReason": stream.error_reason if stream else None,
                "isLocal": stream.is_local if stream else False,
            }

        if camera_id:
            camera_id = str(camera_id)
            return metrics.get(camera_id, {
                "cameraId": camera_id,
                "cameraName": "Camera",
                "captureFps": 0.0,
                "detectionFps": 0.0,
                "frameAgeMs": 0.0,
                "inferenceTimeMs": 0.0,
                "detectionsCount": 0,
                "activeRoisCount": 0,
                "status": "offline",
                "errorReason": None,
                "isLocal": False,
            })

        return metrics




