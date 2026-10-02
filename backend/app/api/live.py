import asyncio
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.services.frame_processor import FrameProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["Live Stream"])
ws_router = APIRouter(tags=["WebSocket Stream"])

@ws_router.websocket("/ws/live")
@ws_router.websocket("/ws/live/{camera_id}")
async def websocket_live_stream(websocket: WebSocket, camera_id: str = "default_cam_01"):
    """
    High-performance binary WebSocket endpoint for real-time live camera streams.
    Delivers latest pre-processed JPEG frames to React frontend with low latency and zero queue backpressure.
    """
    logger.info(f"[DIAGNOSTIC] WebSocket request received for /ws/live/{camera_id}")
    logger.info(f"[DIAGNOSTIC] camera_id received: {camera_id}")
    await websocket.accept()
    logger.info(f"[DIAGNOSTIC] WebSocket accepted/active for camera_id: {camera_id}")

    processor = FrameProcessor()
    camera_id = str(camera_id)

    # Ensure background camera stream is initialized
    stream = processor.camera_service.get_stream(camera_id)
    logger.info(f"[DIAGNOSTIC] CameraStream lookup for camera_id: {camera_id} -> stream exists: {stream is not None and stream.is_running}")

    if not stream or not stream.is_running:
        db_cam = None
        if camera_id != "default_cam_01":
            try:
                from bson import ObjectId
                from app.db.database import get_database
                db = get_database()
                if db is not None and ObjectId.is_valid(camera_id):
                    db_cam = await db.cameras.find_one({"_id": ObjectId(camera_id)})
            except Exception as e:
                logger.warning(f"[WEBSOCKET] Error fetching camera from DB for {camera_id}: {e}")

        if db_cam:
            cam_name = db_cam.get("cameraName", "Camera")
            cam_url = db_cam.get("streamUrl", "0")
            logger.info(f"[DIAGNOSTIC] CameraStream start for camera_id: {camera_id}, url: {cam_url}")
            stream = processor.camera_service.get_or_create_stream(camera_id, cam_name, cam_url)
        else:
            logger.info(f"[DIAGNOSTIC] CameraStream start for camera_id: {camera_id}, url: 0")
            stream = processor.camera_service.get_or_create_stream(camera_id, "Primary Camera", 0)

    last_sent_bytes = None
    first_frame_sent_logged = False

    try:
        # Fast Initial Frame Delivery
        ctx = processor.get_context(camera_id)
        with ctx._lock:
            initial_bytes = ctx.latest_jpeg_bytes

        if initial_bytes:
            await websocket.send_bytes(initial_bytes)
            last_sent_bytes = initial_bytes
            logger.info(f"[DIAGNOSTIC] first JPEG sent for camera_id: {camera_id}")
            first_frame_sent_logged = True

        while True:
            await asyncio.sleep(0.05)  # ~20 FPS max frame delivery rate

            stream = processor.camera_service.get_stream(camera_id)
            if not stream or not stream.is_running:
                continue

            ctx = processor.get_context(camera_id, stream.camera_name)
            with ctx._lock:
                latest = ctx.latest_jpeg_bytes

            # Only send when a new frame is produced (prevents duplicate frame transfers)
            if latest and latest != last_sent_bytes:
                await websocket.send_bytes(latest)
                last_sent_bytes = latest
                if not first_frame_sent_logged:
                    logger.info(f"[DIAGNOSTIC] first JPEG sent for camera_id: {camera_id}")
                    first_frame_sent_logged = True

    except WebSocketDisconnect:
        logger.info(f"[WEBSOCKET] Client disconnected cleanly from camera: {camera_id}")
    except Exception as e:
        logger.warning(f"[WEBSOCKET WARNING] Connection closed for camera {camera_id}: {e}")


@router.get("/metrics")
@router.get("/metrics/")
async def get_live_metrics(camera_id: Optional[str] = None):
    """
    Exposes real-time diagnostic performance metrics for all active cameras or a specific camera_id query.
    """
    processor = FrameProcessor()
    return processor.get_metrics(camera_id=camera_id)


@router.get("/metrics/{camera_id}")
@router.get("/{camera_id}/metrics")
async def get_camera_live_metrics(camera_id: str):
    """
    Exposes real-time diagnostic performance metrics for a specific camera ID.
    """
    processor = FrameProcessor()
    return processor.get_metrics(camera_id=camera_id)


@router.get("/")
async def video_feed():
    processor = FrameProcessor()
    return StreamingResponse(
        processor.generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/{camera_id}")
async def camera_video_feed(camera_id: str):
    """
    Streams live MJPEG feed for a specific camera ID (Retained for legacy/fallback compatibility).
    """
    processor = FrameProcessor()
    return StreamingResponse(
        processor.generate_frames(camera_id=camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/detection-status", response_model=Dict[str, Any])
@router.get("/{camera_id}/detection-status", response_model=Dict[str, Any])
async def get_detection_status(camera_id: str = "default_cam_01"):
    processor = FrameProcessor()
    ctx = processor.get_context(camera_id)
    return {
        "cameraId": camera_id,
        "activeRoisCount": len(ctx.rois),
        "rois": ctx.latest_debug_status,
    }
