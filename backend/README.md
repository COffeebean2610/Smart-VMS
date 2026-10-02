# Smart VMS - Backend

This is the FastAPI backend for the Smart Video Management System (VMS).

## Prerequisites

- Python 3.12+
- MongoDB
- OpenCV (with FFmpeg bindings for VideoWriter)

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   Copy `.env.example` to `.env` and update the values.
   ```bash
   cp .env.example .env
   ```

4. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

## Folder Structure (Storage)
```text
backend/storage/
├── snapshots/          # Extracted YOLO bounding box frames
└── recordings/         # 60-second raw MP4 video segments
    └── YYYY-MM-DD/
        └── camera_id/
            └── HH-MM-SS.mp4
```

## Features

### Continuous Video Recording
The `RecordingService` runs concurrently within the `FrameProcessor` loop. It writes incoming frames directly to an `.mp4` file using the `mp4v` codec via OpenCV's `VideoWriter`.
- **Recording Rotation**: The video segment automatically rotates (saves, closes, and opens a new file) every 60 seconds without dropping frames.
- **Event Linking**: Intrusion events fetch the active `recordingId` and the `videoTimestamp` (offset in seconds) from the `RecordingService`. This enables accurate timeline syncing during playback.

### Playback & Timeline
The `/api/recordings/{id}/stream` API returns a Starlette `FileResponse` for the `.mp4` file, which automatically handles HTTP `Range` requests (`206 Partial Content`). This enables instantaneous seeking within the HTML5 `<video>` player on the React frontend.

## API Documentation

Once the server is running, you can access the Swagger UI documentation at:
- `http://localhost:8000/docs`
