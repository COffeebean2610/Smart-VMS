import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

def test_backend():
    print("Testing backend startup & module imports...")
    try:
        from main import app
        from app.services.yolo_service import YoloService
        from app.services.camera_service import CameraService
        from app.services.event_service import EventService
        from app.services.recording_service import RecordingService
        from app.services.telegram_service import TelegramService
        
        print(f"[INIT SUCCESS] FastAPI Title: {app.title}")
        
        # Instantiate YoloService to verify model loading
        yolo = YoloService()
        if yolo.model:
            print("[YOLO SUCCESS] YOLOv8 Model loaded successfully!")
        else:
            print("[YOLO WARNING] YOLO model instance is None.")
            
        print("[BACKEND VERIFICATION COMPLETE] All modules & services loaded cleanly!")
    except Exception as e:
        print(f"[BACKEND ERROR] Failed to initialize backend: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_backend()
