import asyncio
import logging
import os
from datetime import datetime
from typing import List, Optional

import httpx
from app.core.paths import load_environment
from app.core.config_store import get_telegram_config

load_environment()

logger = logging.getLogger(__name__)


class TelegramService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # Reload configuration from secure config_store / env
        load_environment()
        config = get_telegram_config()
        self.enabled = config["enabled"]
        self.bot_token = config["botToken"]

        raw_chat_id = config["chatId"]
        self.chat_ids: List[str] = [
            cid.strip()
            for cid in raw_chat_id.split(",")
            if cid.strip()
        ]
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        if not hasattr(self, "sent_event_ids"):
            self.sent_event_ids = set()

    def reload_config(self):
        """Forces re-reading of stored configuration."""
        self._initialize()

    def is_configured(self) -> bool:
        self._initialize()
        return bool(self.enabled and self.bot_token and len(self.chat_ids) > 0)

    async def send_media_group(self, photo_path: str, video_path: str, caption: str) -> bool:
        """
        Sends an album group containing photo and video in a single unified message object.
        """
        if not self.is_configured():
            return False

        if not (photo_path and os.path.exists(photo_path) and os.path.getsize(photo_path) > 0):
            return False
        if not (video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 0):
            return False

        if os.path.getsize(video_path) > 50 * 1024 * 1024:
            logger.warning("[TELEGRAM] Video exceeds 50MB for media group.")
            return False

        url = f"{self.base_url}/sendMediaGroup"
        success_count = 0

        import json
        media_payload = [
            {
                "type": "photo",
                "media": "attach://photo",
                "caption": caption,
                "parse_mode": "HTML",
            },
            {
                "type": "video",
                "media": "attach://video",
            },
        ]

        try:
            filename_photo = os.path.basename(photo_path)
            filename_video = os.path.basename(video_path)

            with open(photo_path, "rb") as f_p, open(video_path, "rb") as f_v:
                photo_bytes = f_p.read()
                video_bytes = f_v.read()

            async with httpx.AsyncClient(timeout=60.0) as client:
                for cid in self.chat_ids:
                    files = {
                        "photo": (filename_photo, photo_bytes, "image/jpeg"),
                        "video": (filename_video, video_bytes, "video/mp4"),
                    }
                    data = {
                        "chat_id": cid,
                        "media": json.dumps(media_payload),
                    }
                    try:
                        response = await client.post(url, data=data, files=files)
                        if response.status_code == 200:
                            logger.info(f"[TELEGRAM] Unified media group sent successfully to {cid}")
                            success_count += 1
                        else:
                            logger.warning(f"[TELEGRAM] sendMediaGroup returned HTTP {response.status_code}: {response.text}")
                    except Exception as e:
                        logger.warning(f"[TELEGRAM ERROR] sendMediaGroup failed for {cid}: {e}")
        except Exception as e:
            logger.error(f"[TELEGRAM ERROR] Failed to read files for media group: {e}")

        return success_count > 0

    async def send_intrusion_notification(
        self,
        event_id: str,
        camera_name: str,
        roi_name: str,
        detection_source: str,
        confidence: float,
        timestamp: Optional[datetime] = None,
        snapshot_path: Optional[str] = None,
        video_path: Optional[str] = None,
    ) -> bool:
        """
        Orchestrates exactly ONE unified Telegram notification per intrusion event.
        Guarantees event-level deduplication via event_id.
        """
        if not self.is_configured():
            return False

        event_id_str = str(event_id)
        if hasattr(self, "sent_event_ids") and event_id_str in self.sent_event_ids:
            logger.info(f"[TELEGRAM] Notification already sent for event {event_id_str}. Skipping duplicate.")
            return False

        if not hasattr(self, "sent_event_ids"):
            self.sent_event_ids = set()
        self.sent_event_ids.add(event_id_str)

        logger.info(f"[TELEGRAM] Sending unified intrusion notification for event {event_id_str}...")

        ts = timestamp or datetime.now()
        time_str = ts.strftime("%d %b %Y, %H:%M:%S")
        conf_val = float(confidence) if confidence is not None else 0.0
        conf_str = f"{int(conf_val * 100)}%" if conf_val <= 1.0 else f"{int(conf_val)}%"
        source_label = str(detection_source).replace("+", " + ").title()

        alert_text = (
            f"🚨 <b>SMART VMS — INTRUSION ALERT</b>\n\n"
            f"📷 <b>Camera:</b> {camera_name}\n"
            f"📍 <b>Zone:</b> {roi_name}\n"
            f"🎯 <b>Detection:</b> {source_label}\n"
            f"🎯 <b>Confidence:</b> {conf_str}\n"
            f"🕐 <b>Time:</b> {time_str}\n\n"
            f"⚠️ <i>Movement detected inside the configured security zone.</i>"
        )

        has_snapshot = bool(snapshot_path and os.path.exists(snapshot_path) and os.path.getsize(snapshot_path) > 0)
        has_video = bool(video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 0)

        # Case 1: Both snapshot and video are available -> Try unified Media Group (album)
        if has_snapshot and has_video:
            media_group_sent = await self.send_media_group(snapshot_path, video_path, alert_text)
            if media_group_sent:
                return True

            # Fallback if sendMediaGroup returned error: send photo with caption, then video
            photo_sent = await self.send_telegram_photo(snapshot_path, caption=alert_text)
            if photo_sent:
                await self.send_telegram_video(video_path, caption="🎥 <b>Intrusion Recording</b>")
                return True
            else:
                return await self.send_telegram_video(video_path, caption=alert_text)

        # Case 2: Only snapshot is available
        if has_snapshot:
            caption = alert_text + "\n\n🎥 <i>Recording unavailable</i>"
            return await self.send_telegram_photo(snapshot_path, caption=caption)

        # Case 3: Only video is available
        if has_video:
            caption = alert_text + "\n\n📸 <i>Snapshot unavailable</i>"
            return await self.send_telegram_video(video_path, caption=caption)

        # Case 4: Neither is available -> Send text alert
        text_only = alert_text + "\n\n📸 <i>Snapshot unavailable</i>\n🎥 <i>Recording unavailable</i>"
        return await self.send_telegram_message(text_only)

    async def send_telegram_message(self, text: str) -> bool:
        """
        Sends a text message to all configured Telegram chat recipients.
        """
        if not self.is_configured():
            logger.debug("[TELEGRAM] Notifications disabled or credentials missing.")
            return False

        logger.info(f"[TELEGRAM] Sending message to {len(self.chat_ids)} recipient(s)...")
        url = f"{self.base_url}/sendMessage"
        success_count = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            for cid in self.chat_ids:
                payload = {
                    "chat_id": cid,
                    "text": text,
                    "parse_mode": "HTML",
                }
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        logger.info(f"[TELEGRAM] Message sent successfully to {cid}")
                        success_count += 1
                    else:
                        logger.error(f"[TELEGRAM ERROR] Failed to send to {cid}: HTTP {response.status_code} - {response.text}")
                except Exception as e:
                    logger.error(f"[TELEGRAM ERROR] Failed to send to {cid}: {e}")

        return success_count > 0

    async def send_telegram_photo(self, photo_path: str, caption: str = "") -> bool:
        """
        Sends an image file to all configured Telegram chat recipients.
        """
        if not self.is_configured():
            return False

        if not os.path.exists(photo_path):
            logger.warning(f"[TELEGRAM] Snapshot unavailable (file does not exist): {photo_path}")
            return False

        file_size = os.path.getsize(photo_path)
        if file_size == 0:
            logger.warning(f"[TELEGRAM] Snapshot unavailable (0 bytes): {photo_path}")
            return False

        logger.info(f"[TELEGRAM] Sending snapshot to {len(self.chat_ids)} recipient(s): {photo_path} ({file_size} bytes)")
        url = f"{self.base_url}/sendPhoto"
        success_count = 0

        try:
            filename = os.path.basename(photo_path)
            with open(photo_path, "rb") as f:
                photo_bytes = f.read()

            async with httpx.AsyncClient(timeout=20.0) as client:
                for cid in self.chat_ids:
                    files = {"photo": (filename, photo_bytes, "image/jpeg")}
                    data = {"chat_id": cid, "caption": caption, "parse_mode": "HTML"}
                    try:
                        response = await client.post(url, data=data, files=files)
                        if response.status_code == 200:
                            logger.info(f"[TELEGRAM] Snapshot sent successfully to {cid}")
                            success_count += 1
                        else:
                            logger.error(f"[TELEGRAM ERROR] Failed to send snapshot to {cid}: HTTP {response.status_code} - {response.text}")
                    except Exception as e:
                        logger.error(f"[TELEGRAM ERROR] Failed to send snapshot to {cid}: {e}")
        except Exception as e:
            logger.error(f"[TELEGRAM ERROR] Failed to read snapshot file: {e}")

        return success_count > 0

    async def send_telegram_video(self, video_path: str, caption: str = "") -> bool:
        """
        Sends a video clip to all configured Telegram chat recipients.
        """
        if not self.is_configured():
            return False

        if not os.path.exists(video_path):
            logger.warning(f"[TELEGRAM] Video unavailable (file does not exist): {video_path}")
            return False

        file_size = os.path.getsize(video_path)
        if file_size == 0:
            logger.warning(f"[TELEGRAM] Video unavailable (0 bytes): {video_path}")
            return False

        # Telegram bot API limit for sendVideo is 50MB
        if file_size > 50 * 1024 * 1024:
            logger.warning(f"[TELEGRAM ERROR] Video size exceeds Telegram 50MB limit: {file_size} bytes")
            return False

        logger.info(f"[TELEGRAM] Sending video recording to {len(self.chat_ids)} recipient(s): {video_path} ({file_size} bytes)")
        url = f"{self.base_url}/sendVideo"
        success_count = 0

        try:
            filename = os.path.basename(video_path)
            with open(video_path, "rb") as f:
                video_bytes = f.read()

            async with httpx.AsyncClient(timeout=60.0) as client:
                for cid in self.chat_ids:
                    files = {"video": (filename, video_bytes, "video/mp4")}
                    data = {"chat_id": cid, "caption": caption, "parse_mode": "HTML"}
                    try:
                        response = await client.post(url, data=data, files=files)
                        if response.status_code == 200:
                            logger.info(f"[TELEGRAM] Video sent successfully to {cid}")
                            success_count += 1
                        else:
                            logger.error(f"[TELEGRAM ERROR] Failed to send video to {cid}: HTTP {response.status_code} - {response.text}")
                    except Exception as e:
                        logger.error(f"[TELEGRAM ERROR] Failed to send video to {cid}: {e}")
        except Exception as e:
            logger.error(f"[TELEGRAM ERROR] Failed to read video file: {e}")

        return success_count > 0

    async def send_intrusion_text_alert(
        self,
        camera_name: str,
        roi_name: str,
        detection_source: str,
        confidence: float,
        timestamp: Optional[datetime] = None,
    ):
        """
        Legacy text alert wrapper.
        """
        ts = timestamp or datetime.now()
        time_str = ts.strftime("%d %b %Y, %H:%M:%S")
        conf_str = f"{int(confidence * 100)}%" if confidence <= 1.0 else f"{int(confidence)}%"
        source_label = detection_source.replace("+", " + ").title()

        text = (
            f"🚨 <b>SMART VMS — INTRUSION ALERT</b>\n\n"
            f"📷 <b>Camera:</b> {camera_name}\n"
            f"📍 <b>Zone:</b> {roi_name}\n"
            f"🎯 <b>Detection:</b> {source_label}\n"
            f"🎯 <b>Confidence:</b> {conf_str}\n"
            f"🕐 <b>Time:</b> {time_str}\n\n"
            f"⚠️ <i>Movement detected inside the configured security zone.</i>"
        )
        await self.send_telegram_message(text)

    async def send_snapshot_alert(
        self,
        snapshot_path: str,
        camera_name: str,
        roi_name: str,
        confidence: float,
        timestamp: Optional[datetime] = None,
    ):
        """
        Legacy snapshot alert wrapper.
        """
        ts = timestamp or datetime.now()
        time_str = ts.strftime("%d %b %Y, %H:%M:%S")
        conf_str = f"{int(confidence * 100)}%" if confidence <= 1.0 else f"{int(confidence)}%"

        caption = (
            f"🚨 <b>Intrusion Snapshot</b>\n\n"
            f"Camera: {camera_name}\n"
            f"Zone: {roi_name}\n"
            f"Confidence: {conf_str}\n"
            f"Time: {time_str}"
        )
        await self.send_telegram_photo(snapshot_path, caption=caption)

    async def send_recording_alert(
        self,
        video_path: str,
        camera_name: str,
        roi_name: str,
        duration: float,
        timestamp: Optional[datetime] = None,
    ):
        """
        Legacy recording alert wrapper.
        """
        ts = timestamp or datetime.now()
        time_str = ts.strftime("%d %b %Y, %H:%M:%S")

        caption = (
            f"🎥 <b>Intrusion Recording</b>\n\n"
            f"Camera: {camera_name}\n"
            f"Zone: {roi_name}\n"
            f"Duration: {duration:.1f}s\n"
            f"Time: {time_str}"
        )
        await self.send_telegram_video(video_path, caption=caption)
