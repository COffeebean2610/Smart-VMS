import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import connect_to_mongo, close_mongo_connection, get_database
from app.api import cameras, events, roi, dashboard, live, recordings, storage, notifications, system
from app.core.paths import (
    load_environment,
    get_storage_dir,
    get_snapshots_dir,
    get_recordings_dir,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

load_environment()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        loop = asyncio.get_running_loop()
        logging.info(f"[MONGO] Main event loop id: {id(loop)}")

        from app.services.frame_processor import FrameProcessor
        from app.services.recording_service import RecordingService
        FrameProcessor().set_main_event_loop(loop)
        RecordingService().set_event_loop(loop)

        connected = await connect_to_mongo()
        if connected:
            db = get_database()
            if db is not None:
                count = await db.cameras.count_documents({})
                if count == 0:
                    from datetime import datetime
                    await db.cameras.insert_one({
                        "cameraName": "Default Webcam",
                        "cameraType": "Laptop Webcam",
                        "streamUrl": "0",
                        "location": "Primary Monitoring Station",
                        "description": "Integrated camera sensor",
                        "status": "online",
                        "fps": 30.0,
                        "resolution": "640x480",
                        "lastSeen": datetime.utcnow(),
                        "createdAt": datetime.utcnow(),
                    })
                    logging.info("Default webcam seeded into MongoDB.")
            
            # Populate active ROIs from MongoDB into FrameProcessor contexts
            await FrameProcessor().update_rois()
            logging.info("[STARTUP] ROIs loaded into FrameProcessor contexts successfully.")
        else:
            logging.warning("[STARTUP] MongoDB Atlas unavailable at startup. Backend starting in resilient mode.")
    except Exception as e:
        logging.error(f"[STARTUP WARNING] Database startup check: {e}")
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "Smart Video Management System (VMS)"),
    version=os.getenv("VERSION", "0.1.0"),
    description="Backend API for Smart VMS Prototype",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(cameras.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(roi.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(live.router, prefix="/api")
app.include_router(live.ws_router)
app.include_router(recordings.router, prefix="/api")
app.include_router(storage.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(system.router, prefix="/api")

# Mount Static Files for Snapshots and Recordings
STORAGE_DIR = get_storage_dir()
SNAPSHOTS_DIR = get_snapshots_dir()
RECORDINGS_DIR = get_recordings_dir()

@app.get("/storage/{filepath:path}", tags=["Storage"])
async def serve_storage_file(filepath: str):
    # 1. Primary: Packaged runtime storage (%LOCALAPPDATA%\SmartVMS\storage\)
    primary = get_storage_dir() / filepath
    if primary.exists() and primary.is_file():
        return FileResponse(str(primary))
    
    # 2. Legacy backend/storage fallback
    from pathlib import Path
    legacy_backend = Path.cwd() / "backend" / "storage" / filepath
    if legacy_backend.exists() and legacy_backend.is_file():
        return FileResponse(str(legacy_backend))

    from app.core.paths import get_base_dir
    base_file = get_base_dir() / "storage" / filepath
    if base_file.exists() and base_file.is_file():
        return FileResponse(str(base_file))

    # 3. Legacy root/storage fallback
    legacy_root = Path.cwd() / "storage" / filepath
    if legacy_root.exists() and legacy_root.is_file():
        return FileResponse(str(legacy_root))

    raise HTTPException(status_code=404, detail=f"Storage file '{filepath}' not found")

app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Welcome to Smart VMS API"}

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "Smart VMS Backend"}


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Smart VMS Standalone Backend Server")
    parser.add_argument("--host", type=str, default=os.getenv("HOST", "127.0.0.1"), help="Host IP address to bind")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)), help="Port number to bind")
    args = parser.parse_args()

    logging.info(f"[BACKEND ENTRY] Starting Smart VMS backend server on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


