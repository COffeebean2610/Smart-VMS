import logging
import threading
import time
from typing import Dict, Optional

import cv2

logger = logging.getLogger(__name__)


def is_local_webcam(url) -> bool:
    """
    Checks if a stream URL / identifier refers to a local hardware webcam index.
    """
    if isinstance(url, int):
        return True
    if isinstance(url, str):
        clean = url.strip()
        if clean.isdigit() or clean in ("0", "0.0"):
            return True
    return False


class CameraStream:
    """
    Dedicated background capture stream for a single camera.
    Uses a latest-frame buffer to discard stale frames and guarantee low latency.
    """
    def __init__(self, camera_id: str, camera_name: str, stream_url):
        self.camera_id = str(camera_id)
        self.camera_name = str(camera_name)
        self.stream_url = self._parse_url(stream_url)
        self.is_local = is_local_webcam(self.stream_url)
        self.cap = None
        self.is_running = False
        self.error_reason = None
        self.thread = None
        self._lock = threading.Lock()
        
        # Latest frame state & 5-second rolling pre-intrusion buffer (100 frames at ~20 FPS)
        from collections import deque
        self.frame_buffer = deque(maxlen=100)
        self.latest_raw_frame = None
        self.latest_frame_time = 0.0
        self.capture_fps = 0.0
        self.frames_captured = 0
        self.last_fps_calc = time.time()

    def _parse_url(self, url):
        if isinstance(url, str):
            url = url.strip()
            if url in ("0", "0.0"):
                return 0
        return url

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        logger.info(f"[CAMERA STREAM] Starting capture thread for '{self.camera_name}' ({self.camera_id}) at: {self.stream_url}")
        
        # Open camera
        if self.is_local:
            dev_idx = int(self.stream_url) if isinstance(self.stream_url, str) else self.stream_url
            import sys
            if sys.platform.startswith("win"):
                self.cap = cv2.VideoCapture(dev_idx, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(dev_idx)
            else:
                self.cap = cv2.VideoCapture(dev_idx)

            if self.cap and self.cap.isOpened():
                # Configure local webcam to safe compatible resolution: 640x480 @ 30 FPS
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)

                actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_fps = round(self.cap.get(cv2.CAP_PROP_FPS), 1)
                logger.info(f"[CAMERA STREAM] Local webcam configured: {actual_w}x{actual_h} @ {actual_fps} FPS")
        else:
            self.cap = cv2.VideoCapture(self.stream_url)

        # Minimize buffer size for network streams
        if not self.is_local and isinstance(self.stream_url, str) and (
            self.stream_url.startswith("rtsp") or self.stream_url.startswith("http")
        ):
            try:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

        if not self.cap or not self.cap.isOpened():
            if self.is_local:
                self.error_reason = "camera_blocked"
                logger.warning(f"[CAMERA STREAM ERROR] Local webcam '{self.camera_name}' access blocked by Windows or device unavailable.")
            else:
                self.error_reason = "connection_failed"
                logger.error(f"[CAMERA STREAM ERROR] Failed to open camera '{self.camera_name}' at {self.stream_url}")
            self.is_running = False
            return

        logger.info(f"[DIAGNOSTIC] VideoCapture opened for camera_id: {self.camera_id}")
        logger.info(f"[CAMERA STREAM SUCCESS] Camera '{self.camera_name}' connected.")
        fail_count = 0
        first_read_logged = False

        while self.is_running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.5)
                continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                fail_count += 1
                if self.is_local and fail_count >= 3:
                    self.error_reason = "camera_blocked"
                    logger.warning(f"[CAMERA STREAM] Local webcam '{self.camera_name}' read failed repeatedly (camera access blocked or disconnected).")
                else:
                    logger.warning(f"[CAMERA STREAM] Camera '{self.camera_name}' read failed. Reconnecting in 2s...")
                time.sleep(2)
                if self.cap:
                    self.cap.release()
                if self.is_local:
                    dev_idx = int(self.stream_url) if isinstance(self.stream_url, str) else self.stream_url
                    self.cap = cv2.VideoCapture(dev_idx)
                    if self.cap and self.cap.isOpened():
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        self.cap.set(cv2.CAP_PROP_FPS, 30)
                else:
                    self.cap = cv2.VideoCapture(self.stream_url)
                continue

            # Successful frame read reset error
            fail_count = 0
            self.error_reason = None
            if not first_read_logged:
                logger.info(f"[DIAGNOSTIC] first frame successfully read for camera_id: {self.camera_id}")
                first_read_logged = True

            # Update latest frame under lock (Discarding stale unread frames)
            now = time.time()
            with self._lock:
                self.latest_raw_frame = frame
                self.latest_frame_time = now
                self.frame_buffer.append(frame.copy())
                self.frames_captured += 1

                # Calculate capture FPS
                elapsed = now - self.last_fps_calc
                if elapsed >= 1.0:
                    self.capture_fps = round(self.frames_captured / elapsed, 1)
                    self.frames_captured = 0
                    self.last_fps_calc = now

            # Sleep tiny amount to yield CPU if capture rate is very high
            time.sleep(0.005)

        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info(f"[CAMERA STREAM STOPPED] Stream '{self.camera_name}' stopped.")

    def get_latest_raw_frame(self):
        """
        Returns (frame, frame_time, frame_age_ms).
        """
        with self._lock:
            if self.latest_raw_frame is None:
                return None, 0.0, 0.0
            frame_copy = self.latest_raw_frame.copy()
            frame_time = self.latest_frame_time
            frame_age_ms = round((time.time() - frame_time) * 1000, 1)
            return frame_copy, frame_time, frame_age_ms

    def get_pre_buffer(self):
        """
        Returns snapshot list of pre-intrusion buffer frames.
        """
        with self._lock:
            return list(self.frame_buffer)

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)


class CameraService:
    """
    Central Manager for all simultaneous camera streams.
    """
    streams: Dict[str, CameraStream] = {}
    active_camera_id: str = "default_cam_01"
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CameraService, cls).__new__(cls)
            cls._instance.streams = {}
            cls._instance.active_camera_id = "default_cam_01"
        return cls._instance

    def get_or_create_stream(self, camera_id: str, camera_name: str, url) -> CameraStream:
        camera_id = str(camera_id)
        logger.info(f"[DIAGNOSTIC] CameraStream lookup for camera_id: {camera_id}")

        parsed_url = 0 if (isinstance(url, str) and url.strip() in ("0", "0.0")) else url
        if is_local_webcam(parsed_url):
            for existing_id, existing_stream in list(self.streams.items()):
                if existing_id != camera_id and existing_stream.is_running and existing_stream.is_local:
                    logger.info(f"[CAMERA SERVICE] Stopping conflicting local webcam stream for camera '{existing_id}' to allow '{camera_id}' access.")
                    existing_stream.stop()
                    del self.streams[existing_id]

        if camera_id in self.streams:
            stream = self.streams[camera_id]
            if str(stream.stream_url) != str(url) and url is not None:
                logger.info(f"[DIAGNOSTIC] CameraStream start for camera_id: {camera_id}, url: {url}")
                stream.stop()
                stream = CameraStream(camera_id, camera_name, url)
                self.streams[camera_id] = stream
                stream.start()
            elif not stream.is_running:
                logger.info(f"[DIAGNOSTIC] CameraStream start for camera_id: {camera_id}, url: {url}")
                stream.start()
            return stream

        logger.info(f"[DIAGNOSTIC] CameraStream start for camera_id: {camera_id}, url: {url}")
        stream = CameraStream(camera_id, camera_name, url)
        self.streams[camera_id] = stream
        stream.start()
        return stream

    def set_active_camera(self, url, camera_id: str = "default_cam_01", camera_name: str = "Primary Camera"):
        self.active_camera_id = str(camera_id)
        return self.get_or_create_stream(camera_id, camera_name, url)

    def get_stream(self, camera_id: str) -> Optional[CameraStream]:
        return self.streams.get(str(camera_id))

    def stop_stream(self, camera_id: str):
        camera_id = str(camera_id)
        if camera_id in self.streams:
            self.streams[camera_id].stop()
            del self.streams[camera_id]

    def stop_all(self):
        for stream in list(self.streams.values()):
            stream.stop()
        self.streams.clear()

    @staticmethod
    def test_connection(url):
        is_local = is_local_webcam(url)
        if is_local:
            dev_idx = int(url) if isinstance(url, str) else url
            import sys
            if sys.platform.startswith("win"):
                cap = cv2.VideoCapture(dev_idx, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(dev_idx)
            else:
                cap = cv2.VideoCapture(dev_idx)

            if not cap or not cap.isOpened():
                return False, 0, (0, 0), "camera_blocked"

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)

            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = round(cap.get(cv2.CAP_PROP_FPS), 1)
            logger.info(f"[CAMERA SERVICE TEST] Local webcam configured: {actual_w}x{actual_h} @ {actual_fps} FPS")

            ret, frame = cap.read()
            if ret and frame is not None:
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps == 0 or fps != fps:
                    fps = 30.0
                h, w = frame.shape[:2]
                cap.release()
                return True, fps, (w, h), None
            cap.release()
            return False, 0, (0, 0), "camera_blocked"
        else:
            if isinstance(url, str):
                url = url.strip()
            cap = cv2.VideoCapture(url)
            if isinstance(url, str) and (url.startswith("rtsp") or url.startswith("http")):
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

            if not cap or not cap.isOpened():
                return False, 0, (0, 0), "connection_failed"

            ret, frame = cap.read()
            if ret and frame is not None:
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps == 0 or fps != fps:
                    fps = 30.0
                h, w = frame.shape[:2]
                cap.release()
                return True, fps, (w, h), None

            cap.release()
            return False, 0, (0, 0), "connection_failed"


