# Changelog

All notable changes to the Smart VMS project will be documented in this file.

## [1.0.0] - 2026-08-07

### Added
- **Final Phase: Analytics Dashboard & Polish**
  - Replaced dummy stats with dynamic Recharts in `Dashboard.jsx`.
  - Added Live Alert Panel fetching real-time MongoDB events.
  - Implemented `Storage.jsx` page for disk usage and retention stats.
  - Added CSV Export functionality to `Events.jsx` and `Recordings.jsx`.
  
- **Phase 4: Theme & Camera Management**
  - Next-themes equivalent `ThemeProvider` implementation for System/Dark/Light modes.
  - Interactive Theme toggle in `AdminLayout.jsx` and `Settings.jsx`.
  - Full CRUD `CameraManagement.jsx` page supporting multiple streams.
  - Camera Selector dropdown added to `LiveMonitoring.jsx` for dynamic switching.

- **Phase 3: Video Recording & Timeline Playback**
  - OpenCV-based continuous background recording, segmenting every 60 seconds into H.264 `.mp4`.
  - Synchronized custom `VideoPlayer` component with event markers mapping to video timestamps.
  - HTTP 206 Partial Content support via FastAPI `FileResponse`.

- **Phase 2: YOLO AI & Intrusion Detection**
  - Live OpenCV frame MJPEG streaming via FastAPI.
  - `roi_service.py` checking Ray-Casting Algorithm / Polygon Intersections.
  - Ultralytics YOLOv8 inference yielding `class 0` (person) confidence scores.
  - Snapshot saving upon intrusion detection.

- **Phase 1: Foundation**
  - Initial scaffolding of React, Vite, Tailwind v4, and shadcn/ui.
  - `AdminLayout.jsx` sidebar setup.
  - Asynchronous Motor MongoDB connection singleton.
