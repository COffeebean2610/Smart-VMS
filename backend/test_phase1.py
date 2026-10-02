import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.core.paths import (
    is_packaged,
    get_base_dir,
    get_model_path,
    get_app_data_dir,
    get_storage_dir,
    get_snapshots_dir,
    get_recordings_dir,
    resolve_storage_relative_path,
    get_env_path,
)

def test_paths():
    print("==========================================")
    print("RUNNING PHASE 1 PATH FOUNDATION TESTS")
    print("==========================================")

    # 1. Test Packaged Flag
    packaged = is_packaged()
    print(f"[TEST 1] is_packaged(): {packaged} (Expected: False in dev)")
    assert packaged == False, "Expected is_packaged() to be False in development"

    # 2. Test Base Dir
    base_dir = get_base_dir()
    print(f"[TEST 2] get_base_dir(): {base_dir}")
    assert base_dir.exists(), f"Base dir does not exist: {base_dir}"

    # 3. Test Model Path
    model_path = get_model_path("yolov8n.pt")
    print(f"[TEST 3] get_model_path('yolov8n.pt'): {model_path}")
    assert model_path.exists(), f"YOLO model file not found at: {model_path}"

    # 4. Test Storage Directories
    app_data = get_app_data_dir()
    storage_dir = get_storage_dir()
    snapshots_dir = get_snapshots_dir()
    recordings_dir = get_recordings_dir()

    print(f"[TEST 4a] get_app_data_dir(): {app_data}")
    print(f"[TEST 4b] get_storage_dir(): {storage_dir}")
    print(f"[TEST 4c] get_snapshots_dir(): {snapshots_dir}")
    print(f"[TEST 4d] get_recordings_dir(): {recordings_dir}")

    assert storage_dir.exists(), "Storage directory does not exist"
    assert snapshots_dir.exists(), "Snapshots directory does not exist"
    assert recordings_dir.exists(), "Recordings directory does not exist"

    # 5. Test Relative Path Resolution
    rel_path_1 = "/storage/snapshots/test_image.jpg"
    resolved_1 = resolve_storage_relative_path(rel_path_1)
    print(f"[TEST 5a] resolve('{rel_path_1}'): {resolved_1}")
    assert resolved_1 == snapshots_dir / "test_image.jpg", f"Unexpected resolution: {resolved_1}"

    rel_path_2 = "storage\\recordings\\test_video.mp4"
    resolved_2 = resolve_storage_relative_path(rel_path_2)
    print(f"[TEST 5b] resolve('{rel_path_2}'): {resolved_2}")
    assert resolved_2 == recordings_dir / "test_video.mp4", f"Unexpected resolution: {resolved_2}"

    # 6. Test Env Path
    env_path = get_env_path()
    print(f"[TEST 6] get_env_path(): {env_path}")
    assert env_path.exists(), f"Environment file not found at: {env_path}"

    print("==========================================")
    print("ALL PHASE 1 PATH TESTS PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    test_paths()
