import sys
import os
import torch
import torchvision
import ultralytics
from ultralytics import YOLO

def test_dev():
    print("==========================================")
    print("DEVELOPMENT TORCH / TORCHVISION DIAGNOSTIC")
    print("==========================================")
    print(f"Python: {sys.version}")
    print(f"PyTorch version: {torch.__version__}")
    print(f"TorchVision version: {torchvision.__version__}")
    print(f"Ultralytics version: {ultralytics.__version__}")
    
    # 1. Test NMS operator directly
    try:
        ops = torch.ops.torchvision.nms
        print(f"[NMS TEST] torch.ops.torchvision.nms operator exists: {ops}")
    except Exception as e:
        print(f"[NMS TEST ERROR] {e}")

    # 2. Test NMS function call
    try:
        boxes = torch.tensor([[10.0, 10.0, 20.0, 20.0], [11.0, 11.0, 21.0, 21.0]])
        scores = torch.tensor([0.9, 0.8])
        keep = torchvision.ops.nms(boxes, scores, iou_threshold=0.5)
        print(f"[NMS EXECUTION SUCCESS] Keep indices: {keep}")
    except Exception as e:
        print(f"[NMS EXECUTION ERROR] {e}")

    # 3. Test YOLO Model Predict
    try:
        model_path = os.path.join("models", "yolov8n.pt")
        print(f"Loading YOLO model from: {model_path}")
        model = YOLO(model_path)
        dummy_frame = torch.zeros((480, 640, 3), dtype=torch.uint8).numpy()
        results = model(dummy_frame, classes=[0], conf=0.5, verbose=False)
        print(f"[YOLO INFERENCE SUCCESS] Detections count: {len(results)}")
    except Exception as e:
        print(f"[YOLO INFERENCE ERROR] {e}")

if __name__ == "__main__":
    test_dev()
