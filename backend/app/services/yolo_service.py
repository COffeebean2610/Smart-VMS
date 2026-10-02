import logging
import os
import torch

# PyTorch 2.6+ compatibility for Ultralytics YOLO checkpoint loading
_orig_torch_load = torch.load

def _safe_torch_load(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _orig_torch_load(*args, **kwargs)

torch.load = _safe_torch_load

from ultralytics import YOLO

logger = logging.getLogger(__name__)


class YoloService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(YoloService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        from app.core.paths import get_model_path
        logger.info("Initializing YOLO model...")
        model_path = str(get_model_path("yolov8n.pt"))
        try:
            self.model = YOLO(model_path)
            logger.info("YOLO model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.model = None

    def detect_persons(self, frame, conf_threshold=0.5):
        if not self.model:
            logger.error("detect_persons called but YOLO model is None.")
            return []

        # Run inference, classes=[0] filters only 'person'
        results = self.model(frame, classes=[0], conf=conf_threshold, verbose=False)

        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                detections.append(
                    {"bbox": [int(x1), int(y1), int(x2), int(y2)], "confidence": conf}
                )

        if detections:
            logger.info(f"YOLO detected {len(detections)} person(s).")

        return detections
