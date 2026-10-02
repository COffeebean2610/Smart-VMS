import asyncio
import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Optional

import cv2
import imageio_ffmpeg
from bson import ObjectId

from app.db.database import get_database
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class RecordingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RecordingService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        from app.core.paths import get_recordings_dir
        self.recordings_dir = str(get_recordings_dir())
        self.active_recorders = []
        self.telegram_service = TelegramService()
        self.main_event_loop = None

    def set_event_loop(self, loop):
        self.main_event_loop = loop

    def start_event_recording(
        self,
        event_id: str,
        camera_id: str,
        camera_name: str,
        roi_name: str,
        initial_frame,
        width: int,
        height: int,
        fps: float = 20.0,
        duration: float = 10.0,
        detection_source: str = "Intrusion",
        confidence: float = 0.0,
        event_timestamp: Optional[datetime] = None,
        snapshot_path: Optional[str] = None,
    ):
        """
        Starts a 10-second video clip recording on the existing frame stream for camera_id.
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intrusion_{camera_id}_{timestamp_str}.mp4"
        filepath = os.path.join(self.recordings_dir, filename)
        relative_path = f"/storage/recordings/{filename}"

        os.makedirs(self.recordings_dir, exist_ok=True)
        logger.info(f"[RECORDING]\nCamera={camera_id}\nSTART path={filepath}")

        # Test Codec Fallbacks for Windows OpenCV compatibility
        codecs_to_try = [
            ("mp4v", cv2.VideoWriter.fourcc(*"mp4v")),
            ("XVID", cv2.VideoWriter.fourcc(*"XVID")),
            ("MJPG", cv2.VideoWriter.fourcc(*"MJPG")),
        ]

        writer = None
        used_codec = None
        for name, fourcc in codecs_to_try:
            try:
                w = cv2.VideoWriter(filepath, fourcc, max(15.0, fps), (width, height))
                if w and w.isOpened():
                    writer = w
                    used_codec = name
                    break
            except Exception as e:
                logger.warning(f"[RECORDING] Codec {name} failed for camera {camera_id}: {e}")

        if not writer or not writer.isOpened():
            logger.error(f"[RECORDING]\nCamera={camera_id}\nFAILED error=VideoWriter failed to open with any codec for path {filepath}")
            return None

        # Fetch pre-buffer frames
        from app.services.camera_service import CameraService
        stream = CameraService().get_stream(camera_id)
        pre_buffer = stream.get_pre_buffer() if stream else []
        frames_written_cnt = 0
        logger.info(f"[RECORDING]\nCamera={camera_id}\nPREBUFFER_FRAMES={len(pre_buffer)}")

        if pre_buffer:
            for buf_frame in pre_buffer:
                if buf_frame is not None:
                    if buf_frame.shape[1] != width or buf_frame.shape[0] != height:
                        buf_frame = cv2.resize(buf_frame, (width, height))
                    writer.write(buf_frame)
                    frames_written_cnt += 1

        # Write current triggering frame
        if initial_frame is not None:
            if initial_frame.shape[1] != width or initial_frame.shape[0] != height:
                initial_frame = cv2.resize(initial_frame, (width, height))
            writer.write(initial_frame)
            frames_written_cnt += 1

        logger.info(f"[RECORDING]\nCamera={camera_id}\nWriter opened: codec={used_codec}, width={width}, height={height}, fps={fps}, initial_frames={frames_written_cnt}")

        recorder = {
            "event_id": str(event_id),
            "camera_id": str(camera_id),
            "camera_name": str(camera_name),
            "roi_name": str(roi_name),
            "detection_source": str(detection_source),
            "confidence": float(confidence),
            "event_timestamp": event_timestamp or datetime.now(),
            "snapshot_path": snapshot_path,
            "filepath": filepath,
            "relative_path": relative_path,
            "writer": writer,
            "start_time": time.time(),
            "duration": float(duration),
            "frames_written": frames_written_cnt,
            "width": width,
            "height": height,
        }

        self.active_recorders.append(recorder)
        return relative_path

    def write_frame(self, camera_id: str, frame):
        """
        Writes each incoming frame to active recorders MATCHING camera_id.
        """
        camera_id_str = str(camera_id)
        for rec in list(self.active_recorders):
            if rec["camera_id"] == camera_id_str:
                try:
                    h, w = frame.shape[:2]
                    rec_w, rec_h = rec.get("width", w), rec.get("height", h)
                    frame_to_write = frame
                    if w != rec_w or h != rec_h:
                        frame_to_write = cv2.resize(frame, (rec_w, rec_h))

                    rec["writer"].write(frame_to_write)
                    rec["frames_written"] += 1

                    # Check if 10-second window has completed
                    if time.time() - rec["start_time"] >= rec["duration"]:
                        rec["writer"].release()
                        self.active_recorders.remove(rec)
                        self._dispatch_finalize(rec)
                except Exception as e:
                    import traceback
                    logger.error(f"[RECORDING]\nCamera={camera_id_str}\nFAILED error={e}\n{traceback.format_exc()}")
                    if rec in self.active_recorders:
                        try:
                            rec["writer"].release()
                        except Exception:
                            pass
                        self.active_recorders.remove(rec)

    def _dispatch_finalize(self, rec):
        if self.main_event_loop and self.main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._finalize_recording(rec), self.main_event_loop)
        else:
            logger.warning(f"[RECORDING WARNING] Main event loop not running. Finalization delayed for recorder camera {rec.get('camera_id')}.")

    async def _finalize_recording(self, rec):
        filepath = rec["filepath"]
        start_time = rec["start_time"]
        actual_duration = round(time.time() - start_time, 1)

        if not os.path.exists(filepath):
            logger.error(f"[RECORDING]\nCamera={rec['camera_id']}\nFAILED error=Recording file does not exist at {filepath}")
            # Fallback unified notification without video
            try:
                await self.telegram_service.send_intrusion_notification(
                    event_id=rec["event_id"],
                    camera_name=rec.get("camera_name", "Default Webcam"),
                    roi_name=rec.get("roi_name", "ROI"),
                    detection_source=rec.get("detection_source", "Intrusion"),
                    confidence=rec.get("confidence", 0.0),
                    timestamp=rec.get("event_timestamp"),
                    snapshot_path=rec.get("snapshot_path"),
                    video_path=None,
                )
            except Exception as e:
                logger.error(f"[TELEGRAM ERROR] Fallback notification failed: {e}")
            return

        file_size = os.path.getsize(filepath)
        if file_size == 0:
            logger.error(f"[RECORDING]\nCamera={rec['camera_id']}\nFAILED error=Recording file is 0 bytes at {filepath}")
            # Fallback unified notification without video
            try:
                await self.telegram_service.send_intrusion_notification(
                    event_id=rec["event_id"],
                    camera_name=rec.get("camera_name", "Default Webcam"),
                    roi_name=rec.get("roi_name", "ROI"),
                    detection_source=rec.get("detection_source", "Intrusion"),
                    confidence=rec.get("confidence", 0.0),
                    timestamp=rec.get("event_timestamp"),
                    snapshot_path=rec.get("snapshot_path"),
                    video_path=None,
                )
            except Exception as e:
                logger.error(f"[TELEGRAM ERROR] Fallback notification failed: {e}")
            return

        logger.info(f"[RECORDING] Transcoding raw recording for camera {rec['camera_id']} to browser H.264...")

        # Transcode to H.264 (yuv420p + faststart) for instant browser playback
        try:
            temp_h264_path = filepath.replace(".mp4", "_h264.mp4")
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe,
                "-y",
                "-i", filepath,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-preset", "ultrafast",
                temp_h264_path,
            ]
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: subprocess.run(cmd, capture_output=True))
            if res.returncode == 0 and os.path.exists(temp_h264_path) and os.path.getsize(temp_h264_path) > 0:
                os.replace(temp_h264_path, filepath)
                file_size = os.path.getsize(filepath)
                logger.info(f"[RECORDING] Transcoded to browser H.264: {filepath}")
            else:
                logger.warning(f"[RECORDING] FFmpeg transcode returned {res.returncode}. Retaining original file.")
        except Exception as e:
            logger.error(f"[RECORDING ERROR] Error during H.264 transcode: {e}")

        logger.info(f"[RECORDING]\nCamera={rec['camera_id']}\nSUCCESS path={filepath} size={file_size} bytes")

        db = get_database()
        if db is not None:
            rec_id = ObjectId()
            rec_doc = {
                "_id": rec_id,
                "cameraId": rec["camera_id"],
                "filePath": rec["relative_path"],
                "startTime": datetime.fromtimestamp(start_time),
                "endTime": datetime.utcnow(),
                "duration": actual_duration,
                "fileSize": file_size,
                "type": "Intrusion Event",
                "createdAt": datetime.utcnow(),
            }

            try:
                await db.recordings.insert_one(rec_doc)
                logger.info(f"[RECORDING] MongoDB recording created: {rec_id} for camera {rec['camera_id']}")

                if ObjectId.is_valid(rec["event_id"]):
                    await db.events.update_one(
                        {"_id": ObjectId(rec["event_id"])},
                        {
                            "$set": {
                                "videoPath": rec["relative_path"],
                                "recordingId": str(rec_id),
                            }
                        },
                    )
                    logger.info(f"[EVENT] Updated event {rec['event_id']} with video path")
            except Exception as e:
                logger.error(f"[RECORDING ERROR] Failed to save recording to DB: {e}")

        # Send Single Unified Telegram Notification for this Intrusion Event
        try:
            logger.info(f"[TELEGRAM] Sending single unified notification for camera {rec['camera_name']}, event {rec['event_id']}")
            sent_notification = await self.telegram_service.send_intrusion_notification(
                event_id=rec["event_id"],
                camera_name=rec.get("camera_name", "Default Webcam"),
                roi_name=rec.get("roi_name", "ROI"),
                detection_source=rec.get("detection_source", "Intrusion"),
                confidence=rec.get("confidence", 0.0),
                timestamp=rec.get("event_timestamp"),
                snapshot_path=rec.get("snapshot_path"),
                video_path=filepath,
            )
            if sent_notification:
                logger.info("[TELEGRAM] Unified notification sent successfully")
        except Exception as e:
            logger.error(f"[TELEGRAM ERROR] Unified notification failed: {e}")



