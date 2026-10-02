import sys
import os
import json
import urllib.request
import asyncio

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.frame_processor import FrameProcessor

def test_backend_metrics_directly():
    print("==================================================")
    print("TESTING METRICS ENDPOINT IMPLEMENTATION DIRECTLY")
    print("==================================================")

    processor = FrameProcessor()
    
    # Simulate processing a frame for default_cam_01
    ctx = processor.get_context("default_cam_01", "Primary Camera")
    ctx.frames_processed += 10
    ctx.frame_age_ms = 12.5
    ctx.inference_time_ms = 45.2
    ctx.detections_count = 1

    # 1. Test global metrics
    all_metrics = processor.get_metrics()
    print("\n1. FrameProcessor.get_metrics() global result:")
    print(json.dumps(all_metrics, indent=2))

    # 2. Test camera-specific metrics
    cam_metrics = processor.get_metrics("default_cam_01")
    print("\n2. FrameProcessor.get_metrics('default_cam_01') result:")
    print(json.dumps(cam_metrics, indent=2))

    success = ("default_cam_01" in all_metrics) and (cam_metrics.get("cameraId") == "default_cam_01")
    print(f"\nDIRECT METRICS TEST RESULT: {'PASS' if success else 'FAIL'}")
    return success

if __name__ == "__main__":
    test_backend_metrics_directly()
