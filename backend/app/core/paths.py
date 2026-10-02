import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def is_packaged() -> bool:
    """
    Check if the application is running inside a PyInstaller frozen bundle.
    """
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_base_dir() -> Path:
    """
    Get the base directory for bundled read-only resources.
    In Development: Points to backend/ directory (parent of app/).
    In PyInstaller mode: Points to sys._MEIPASS (extracted temporary folder).
    """
    if is_packaged():
        return Path(sys._MEIPASS)
    # File is in backend/app/core/paths.py, so parent.parent.parent is backend/
    return Path(__file__).resolve().parent.parent.parent


def get_bundled_resource_dir(sub_dir: str = "") -> Path:
    """
    Get path to a read-only bundled resource directory (e.g., models, static assets).
    """
    base = get_base_dir()
    return base / sub_dir if sub_dir else base


def get_model_path(model_filename: str = "yolov8n.pt") -> Path:
    """
    Get absolute path to the YOLO model file.
    In Development / PyInstaller:
    1. Check backend/models/<model_filename> (or sys._MEIPASS/models/<model_filename>)
    2. Fallback to project_root/models/<model_filename>
    """
    primary = get_bundled_resource_dir("models") / model_filename
    if primary.exists():
        return primary

    # Fallback for dev mode when models directory is in project root
    fallback = get_base_dir().parent / "models" / model_filename
    if fallback.exists():
        return fallback

    logger.warning(f"[PATH UTILITY] Model file '{model_filename}' not found at {primary} or {fallback}")
    return primary


def get_app_data_dir() -> Path:
    """
    Get the writable user application data directory.
    - If SMARTVMS_DATA_DIR env variable is set, uses that.
    - In PyInstaller/Desktop mode: Uses %LOCALAPPDATA%/SmartVMS (or ~/.smartvms on Linux/macOS).
    - In Development mode: Uses backend/ directory so backend/storage remains default, preserving 100% dev compatibility.
    """
    override = os.getenv("SMARTVMS_DATA_DIR")
    if override:
        path = Path(override)
    elif is_packaged():
        local_app_data = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        path = Path(local_app_data) / "SmartVMS"
    else:
        path = get_base_dir()

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_storage_dir() -> Path:
    """
    Get the main writable storage directory for user media and logs.
    """
    storage = get_app_data_dir() / "storage"
    storage.mkdir(parents=True, exist_ok=True)
    return storage


def get_snapshots_dir() -> Path:
    """
    Get writable directory for camera event snapshot images.
    """
    snapshots = get_storage_dir() / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    return snapshots


def get_recordings_dir() -> Path:
    """
    Get writable directory for camera intrusion video recordings.
    """
    recordings = get_storage_dir() / "recordings"
    recordings.mkdir(parents=True, exist_ok=True)
    return recordings


def resolve_storage_relative_path(relative_path: str) -> Path:
    """
    Resolves a relative storage path (e.g., '/storage/snapshots/xyz.jpg' or 'storage/recordings/abc.mp4')
    to an absolute filesystem path within the centralized writable storage directory.
    """
    clean_rel = relative_path.lstrip("/").lstrip("\\")
    if clean_rel.startswith("storage/") or clean_rel.startswith("storage\\"):
        clean_rel = clean_rel[7:].lstrip("/").lstrip("\\")

    return get_storage_dir() / clean_rel


def get_env_path() -> Path:
    """
    Locates the active .env configuration file.
    """
    if is_packaged():
        app_data_env = get_app_data_dir() / ".env"
        if app_data_env.exists():
            return app_data_env
        exe_env = Path(sys.executable).parent / ".env"
        if exe_env.exists():
            return exe_env
        return app_data_env

    backend_env = get_base_dir() / ".env"
    if backend_env.exists():
        return backend_env

    return get_base_dir().parent / ".env"


def load_environment():
    """
    Loads environment variables from the centralized .env file path.
    """
    env_file = get_env_path()
    if env_file.exists():
        load_dotenv(dotenv_path=str(env_file))
        logger.info(f"[PATH UTILITY] Loaded environment configuration from: {env_file}")
    else:
        load_dotenv()
        logger.info("[PATH UTILITY] Loaded environment from default search path")
