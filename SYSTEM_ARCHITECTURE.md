# System Architecture

Smart VMS uses a decoupled client-server architecture with an integrated asynchronous AI loop.

## High-Level Diagram

```mermaid
graph TD
    A[Browser Client / React SPA] -->|HTTP / REST| B(FastAPI Backend)
    A -->|MJPEG Stream| B
    B -->|PyMongo| C[(MongoDB Atlas)]
    
    subgraph FastAPI Backend
    D[API Routers]
    E[Camera Service]
    F[Frame Processor & YOLO]
    G[Recording Service]
    H[Event & ROI Service]
    
    D --> E
    E --> F
    F -->|Raw Frame| G
    F -->|Intersection True| H
    end
    
    G -->|Write MP4| I[Local Filesystem]
    H -->|Save JPG| I
```

## The Processing Loop

```mermaid
sequenceDiagram
    participant Camera
    participant FrameProcessor
    participant YOLO
    participant ROI_Engine
    participant RecordingService
    participant EventService
    
    Camera->>FrameProcessor: Read Frame (cv2)
    FrameProcessor->>RecordingService: Pass raw frame for MP4 encode
    FrameProcessor->>YOLO: Infer Objects
    YOLO-->>FrameProcessor: Bounding Boxes (Person)
    
    FrameProcessor->>ROI_Engine: Check Box/Polygon Intersection
    alt Intersection == True
        ROI_Engine->>EventService: Trigger Intrusion Event
        EventService->>EventService: Save Snapshot (.jpg)
        EventService->>MongoDB: Insert Event Record
    end
    
    FrameProcessor->>FrameProcessor: Draw Boxes & Polygons
    FrameProcessor->>Browser: Yield MJPEG Frame
```

## File Storage
Recordings are saved locally because streaming large MP4s directly to a cloud provider in real-time is prone to latency and data loss.
- `backend/storage/recordings/` - H.264 encoded MP4 files. Segmented every 60 seconds.
- `backend/storage/snapshots/` - JPG images extracted at the exact frame of intrusion.
