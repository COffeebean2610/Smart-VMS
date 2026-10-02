# Testing Guide

Smart VMS includes multiple points of validation. As this is a prototype, manual integration testing is the primary method of validation.

## 1. Testing the Camera Pipeline

1. Start the FastAPI backend.
2. Go to `http://localhost:5173/camera-management`.
3. Click "Add Camera".
4. Enter `0` for the laptop webcam and click "Test Connection".
5. The backend will attempt `cv2.VideoCapture(url).read()`. A green success message verifies the OpenCV installation and camera driver.

## 2. Testing ROI & AI Intersection

1. Navigate to Live Monitoring (`/cameras`).
2. Draw a rectangle on the left side of the screen. Wait for a person to walk into it.
3. Observe the Backend terminal logs. You should see:
   ```
   [YOLO] Detected Person at (x,y)
   [ROI] Intersection with 'Zone 1': True
   [Event] Intrusion triggered! Snapshot saved.
   ```
4. If it prints `Intersection: False`, the person is outside the ROI.

## 3. Testing Continuous Recording

1. Keep the backend running for at least 65 seconds.
2. The `RecordingService` segments video every 60 seconds.
3. Check `backend/storage/recordings/`. A new `.mp4` file should appear.
4. Try playing the file in VLC. If it does not play, OpenCV may be missing the H.264 codec. Ensure you are using `cv2.VideoWriter_fourcc(*'avc1')`.

## 4. Testing React Video Playback

1. Go to Recordings (`/recordings`).
2. Click "Play" on a recording.
3. The custom `VideoPlayer` modal will open. 
4. Check the browser Network Tab. You should see an initial HTTP 206 request for `/api/recordings/{id}/stream`. If it returns HTTP 200, the browser cannot seek properly. Fast API `FileResponse` automatically handles 206 Partial Content.
