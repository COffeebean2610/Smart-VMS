# API Documentation

The backend is built with FastAPI and runs on `http://localhost:8000`. Swagger documentation is available at `http://localhost:8000/docs`.

## 1. Camera Management (`/api/cameras`)

- **`GET /api/cameras/`**
  - Fetch all configured cameras.
  - *Returns*: `List[CameraSchema]`

- **`POST /api/cameras/`**
  - Add a new camera.
  - *Body*: `{"cameraName": "Main Gate", "type": "ip", "url": "http://..."}`

- **`PUT /api/cameras/{camera_id}`**
  - Update camera details.

- **`DELETE /api/cameras/{camera_id}`**
  - Remove a camera.

- **`POST /api/cameras/test`**
  - Test a camera connection before saving.
  - *Body*: `{"url": "http://..."}`
  - *Returns*: `{"success": True, "message": "Connection successful"}`

- **`POST /api/cameras/connect/{camera_id}`**
  - Switch the active stream to the specified camera.
  - *Returns*: `{"status": "connected"}`

## 2. Live Streaming (`/api/live`)

- **`GET /api/live/stream`** *(Also available at `/api/live`)*
  - Returns a multipart MJPEG stream.
  - *Content-Type*: `multipart/x-mixed-replace; boundary=frame`
  - Uses `StreamingResponse` to continuously yield JPEG bytes.

## 3. Detection Zones (`/api/roi`)

- **`GET /api/roi/`**
  - Fetch all saved Region of Interest (ROI) polygons.

- **`POST /api/roi/`**
  - Save a new ROI.
  - *Body*: `{"zoneName": "Zone 1", "cameraId": "cam1", "coordinates": [{"x": 0.1, "y": 0.2}, ...]}`

- **`DELETE /api/roi/{roi_id}`**
  - Delete an ROI by ID.

## 4. Events (`/api/events`)

- **`GET /api/events/`**
  - Fetch latest events sorted by timestamp descending.

## 5. Recordings (`/api/recordings`)

- **`GET /api/recordings/`**
  - Fetch all recordings metadata.

- **`GET /api/recordings/{recording_id}/stream`**
  - Stream a specific `.mp4` video file using HTTP 206 Partial Content.
  - *Returns*: `FileResponse`

## 6. Dashboard Analytics (`/api/dashboard`)

- **`GET /api/dashboard/`**
  - Returns top-level summary metrics (online cameras, active alerts, total events).

- **`GET /api/dashboard/charts`**
  - Returns aggregated data formatted for Recharts:
    - `eventsPerHour` (Array)
    - `intrusionsByCamera` (Array)
    - `storageUsage` (Array)
    - `detectionDistribution` (Array)
    - `weeklyTrend` (Array)

## 7. Storage (`/api/storage`)

- **`GET /api/storage/`**
  - Returns disk usage statistics and retention windows.
  - *Returns*: `{"totalGB": 500, "usedGB": 250, "freeGB": 250, "usedPercent": 50, ...}`
