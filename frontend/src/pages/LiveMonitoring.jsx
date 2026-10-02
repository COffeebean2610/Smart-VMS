import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { roiService } from '../services/roiService';
import { eventService } from '../services/eventService';
import { cameraService } from '../services/cameraService';
import { Video, AlertTriangle, Activity, Map, Trash2, Camera, Loader2, RefreshCw } from 'lucide-react';
import EventSnapshotImage from '../components/EventSnapshotImage';

function LiveStreamViewer({ cameraId, cameraName, cameraStatus, errorReason, isLocal, rois, currentRect, onMouseDown, onMouseMove, onMouseUp, onRetryCamera }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [imgSrc, setImgSrc] = useState(null);
  
  const wsRef = useRef(null);
  const prevObjectUrlRef = useRef(null);
  const activeCameraRef = useRef(cameraId);
  const imgRef = useRef(null);
  const canvasRef = useRef(null);

  // WebSocket Live Binary Stream Connection Lifecycle
  useEffect(() => {
    if (!cameraId) {
      setLoading(true);
      return;
    }

    setLoading(true);
    setError(false);
    setImgSrc(null);
    activeCameraRef.current = cameraId;

    // WebSocket URL to backend (Forces 127.0.0.1 for local/file protocol to prevent IPv6 ::1 lookup failures in Electron)
    const wsHost = (window.location.protocol === 'file:' || !window.location.hostname || window.location.hostname === 'localhost') 
      ? '127.0.0.1' 
      : window.location.hostname;
    const wsUrl = `ws://${wsHost}:8000/ws/live/${cameraId}`;

    console.log("[DIAGNOSTIC] WebSocket creation for camera:", cameraId, "url:", wsUrl);

    let ws = null;
    try {
      ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = () => {
        if (activeCameraRef.current !== cameraId) return;
        console.log("[DIAGNOSTIC] WebSocket open for camera:", cameraId);
        setError(false);
      };

      ws.onmessage = (event) => {
        // Race Condition Guard: Ignore stale frames from previous camera sockets
        if (activeCameraRef.current !== cameraId) return;
        if (!(event.data instanceof ArrayBuffer)) return;

        try {
          const blob = new Blob([event.data], { type: 'image/jpeg' });
          const newUrl = URL.createObjectURL(blob);

          // Memory Leak Prevention: Revoke previous Blob Object URL
          if (prevObjectUrlRef.current) {
            URL.revokeObjectURL(prevObjectUrlRef.current);
          }
          prevObjectUrlRef.current = newUrl;

          setImgSrc(newUrl);
          setLoading(false);
          setError(false);
        } catch (err) {
          console.error('[WEBSOCKET FRAME ERROR]', err);
        }
      };

      ws.onerror = (err) => {
        if (activeCameraRef.current !== cameraId) return;
        console.log("[DIAGNOSTIC] WebSocket error for camera:", cameraId, err);
        console.error(`[WEBSOCKET ERROR] Stream for camera ${cameraId} failed:`, err);
        setError(true);
        setLoading(false);
      };

      ws.onclose = () => {
        if (activeCameraRef.current !== cameraId) return;
        console.log("[DIAGNOSTIC] WebSocket close for camera:", cameraId);
      };
    } catch (err) {
      console.error('[WEBSOCKET INIT ERROR]', err);
      setError(true);
      setLoading(false);
    }

    return () => {
      // Cleanup: Close WebSocket & revoke object URLs on unmount / camera switch
      if (wsRef.current) {
        wsRef.current.onopen = null;
        wsRef.current.onmessage = null;
        wsRef.current.onerror = null;
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      if (prevObjectUrlRef.current) {
        URL.revokeObjectURL(prevObjectUrlRef.current);
        prevObjectUrlRef.current = null;
      }
    };
  }, [cameraId]);

  // Canvas drawing effect for ROIs
  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    
    if (canvas.clientWidth && canvas.clientHeight) {
      if (canvas.width !== canvas.clientWidth || canvas.height !== canvas.clientHeight) {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
      }
    }

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Filter ROIs for this specific camera
    const filteredRois = rois.filter(r => !r.cameraId || r.cameraId === cameraId);

    filteredRois.forEach(roi => {
      if (roi.coordinates && roi.coordinates.length >= 2) {
        const xs = roi.coordinates.map(p => p.x * canvas.width);
        const ys = roi.coordinates.map(p => p.y * canvas.height);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 2;
        ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);
        ctx.fillStyle = 'rgba(59, 130, 246, 0.2)';
        ctx.fillRect(minX, minY, maxX - minX, maxY - minY);
        
        ctx.fillStyle = '#3b82f6';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText(roi.zoneName, Math.max(0, minX), Math.max(14, minY - 5));
      }
    });

    if (currentRect && currentRect.w > 0 && currentRect.h > 0) {
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 2;
      ctx.strokeRect(currentRect.x, currentRect.y, currentRect.w, currentRect.h);
      ctx.fillStyle = 'rgba(34, 197, 94, 0.2)';
      ctx.fillRect(currentRect.x, currentRect.y, currentRect.w, currentRect.h);
      ctx.fillStyle = '#22c55e';
      ctx.font = 'bold 12px sans-serif';
      ctx.fillText('New ROI', currentRect.x, Math.max(14, currentRect.y - 5));
    }
  }, [rois, currentRect, cameraId]);

  const isBlocked = cameraStatus === 'camera_blocked' || errorReason === 'camera_blocked' || (error && isLocal);

  return (
    <Card className="overflow-hidden relative bg-black flex items-center justify-center min-h-120">
      {/* Loading Overlay */}
      {loading && !error && !isBlocked && (
        <div className="absolute inset-0 z-20 bg-slate-950/90 flex flex-col items-center justify-center text-slate-200">
          <Loader2 className="h-10 w-10 animate-spin text-blue-500 mb-3" />
          <p className="text-sm font-medium">Connecting WebSocket to {cameraName || 'Camera'}...</p>
        </div>
      )}

      {/* Windows Camera Privacy Blocked Overlay */}
      {isBlocked ? (
        <div className="absolute inset-0 z-30 bg-slate-950/95 flex flex-col items-center justify-center p-6 text-center text-slate-200 space-y-3">
          <div className="p-3 bg-red-500/10 text-red-500 rounded-full border border-red-500/30">
            <Camera className="h-10 w-10" />
          </div>
          <div className="space-y-1 max-w-md">
            <h3 className="font-bold text-base text-red-400">Camera Access Blocked by Windows</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Camera access is blocked by Windows. Please enable Camera access for desktop apps in Windows Settings.
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-lg text-left text-xs space-y-1.5 text-slate-400 max-w-sm w-full">
            <p className="font-semibold text-slate-300">Required Windows Settings:</p>
            <p className="flex items-center gap-1.5">• Enable <span className="text-slate-200 font-medium">Camera access</span></p>
            <p className="flex items-center gap-1.5">• Enable <span className="text-slate-200 font-medium">Let desktop apps access your camera</span></p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
            <Button
              variant="default"
              size="sm"
              className="text-xs gap-1.5"
              onClick={() => {
                window.location.href = 'ms-settings:privacy-webcam';
              }}
            >
              Open Windows Settings
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs gap-1.5"
              onClick={() => {
                setLoading(true);
                setError(false);
                if (onRetryCamera) onRetryCamera();
              }}
            >
              <RefreshCw className="h-3.5 w-3.5" /> Retry Camera
            </Button>
          </div>
        </div>
      ) : (
        /* Error Overlay for non-local stream failure */
        error && (
          <div className="absolute inset-0 z-20 bg-slate-950/90 flex flex-col items-center justify-center text-slate-300">
            <Video className="h-12 w-12 mb-3 text-red-400" />
            <p className="font-medium text-slate-200">{cameraName || 'Camera'} — WebSocket stream unavailable</p>
            <Button 
              variant="outline" 
              size="sm" 
              className="mt-3 text-xs gap-1"
              onClick={() => {
                setLoading(true);
                setError(false);
                if (onRetryCamera) onRetryCamera();
              }}
            >
              <RefreshCw className="h-3 w-3" /> Retry Stream
            </Button>
          </div>
        )
      )}


      <div className="relative w-full h-full max-h-180 aspect-video">
        {imgSrc ? (
          <img
            ref={imgRef}
            src={imgSrc}
            alt={`Live Stream - ${cameraName}`}
            className="w-full h-full object-fill rounded-lg"
          />
        ) : (
          <div className="w-full h-full bg-slate-950 flex items-center justify-center text-slate-600 text-xs">
            Waiting for video stream...
          </div>
        )}
        <canvas
          ref={canvasRef}
          className="absolute top-0 left-0 w-full h-full cursor-crosshair rounded-lg z-10"
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseUp}
        />
      </div>
    </Card>
  );
}

export default function LiveMonitoring() {
  const [stats, setStats] = useState({ fps: 30, status: 'Online', latestDetection: 'None' });
  const [events, setEvents] = useState([]);
  const [rois, setRois] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [activeCameraId, setActiveCameraId] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentRect, setCurrentRect] = useState(null);

  const fetchRois = async () => {
    try {
      const data = await roiService.getAll();
      setRois(data);
    } catch (error) {
      console.error("Failed to fetch ROIs:", error);
    }
  };

  const fetchEvents = async () => {
    try {
      const data = await eventService.getAll();
      setEvents(data.slice(0, 5));
      if (data.length > 0) {
        setStats(prev => ({ ...prev, latestDetection: data[0].timestamp }));
      }
    } catch (error) {
      console.error("Failed to fetch events:", error);
    }
  };

  const fetchCameras = async () => {
    try {
      const data = await cameraService.getAll();
      console.log("[DIAGNOSTIC] cameras loaded:", data);
      setCameras(data);
      if (!activeCameraId) {
        const active = data.find(c => c.status === 'online') || data[0];
        if (active) {
          console.log("[DIAGNOSTIC] selected camera ID:", active.id);
          console.log("[DIAGNOSTIC] selected camera URL:", active.streamUrl);
          setActiveCameraId(active.id);
        }
      }
    } catch (error) {
      console.error("Failed to fetch cameras:", error);
    }
  };

  const fetchMetrics = async () => {
    try {
      const data = await cameraService.getMetrics(activeCameraId);
      const m = (data && activeCameraId && data[activeCameraId]) ? data[activeCameraId] : data;
      if (m && typeof m === 'object') {
        setStats(prev => ({
          ...prev,
          captureFps: m.captureFps || 0,
          detectionFps: m.detectionFps || 0,
          frameAgeMs: m.frameAgeMs || 0,
          inferenceTimeMs: m.inferenceTimeMs || 0,
          status: m.status === 'online' ? 'Online' : (m.status === 'camera_blocked' ? 'Camera Blocked' : 'Offline'),
          rawStatus: m.status,
          errorReason: m.errorReason,
          isLocal: m.isLocal,
          activeRois: m.activeRoisCount || 0,
        }));
      }
    } catch (error) {
      console.error("Failed to fetch metrics:", error);
    }
  };

  useEffect(() => {
    console.log("[DIAGNOSTIC] LiveMonitoring mounted");
    fetchRois();
    fetchEvents();
    fetchCameras();
    
    const interval = setInterval(() => {
      fetchEvents();
      fetchMetrics();
    }, 1500);
    return () => clearInterval(interval);
  }, [activeCameraId]);

  const handleMouseDown = (e) => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setIsDrawing(true);
    setCurrentRect({ x, y, w: 0, h: 0, startX: x, startY: y });
  };

  const handleMouseMove = (e) => {
    if (!isDrawing || !currentRect) return;
    const canvas = document.querySelector('canvas');
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setCurrentRect(prev => ({
      ...prev,
      x: Math.min(prev.startX, x),
      y: Math.min(prev.startY, y),
      w: Math.abs(x - prev.startX),
      h: Math.abs(y - prev.startY)
    }));
  };

  const handleMouseUp = () => {
    setIsDrawing(false);
  };

  const handleSaveRoi = async () => {
    if (!currentRect || currentRect.w < 5 || currentRect.h < 5) return;
    
    const canvas = document.querySelector('canvas');
    const canvasWidth = canvas?.clientWidth || canvas?.width || 640;
    const canvasHeight = canvas?.clientHeight || canvas?.height || 480;
    
    const minX = Math.max(0, Math.min(1, currentRect.x / canvasWidth));
    const minY = Math.max(0, Math.min(1, currentRect.y / canvasHeight));
    const maxX = Math.max(0, Math.min(1, (currentRect.x + currentRect.w) / canvasWidth));
    const maxY = Math.max(0, Math.min(1, (currentRect.y + currentRect.h) / canvasHeight));

    const newRoi = {
      zoneName: `ROI_${Math.floor(100 + Math.random() * 900)}`,
      cameraId: activeCameraId || "default_cam_01",
      coordinates: [
        { x: minX, y: minY },
        { x: maxX, y: minY },
        { x: maxX, y: maxY },
        { x: minX, y: maxY }
      ]
    };

    try {
      await roiService.create(newRoi);
      setCurrentRect(null);
      await fetchRois();
    } catch (error) {
      console.error("Failed to save ROI", error);
    }
  };

  const handleDeleteRoi = async (id) => {
    try {
      await roiService.delete(id);
      await fetchRois();
    } catch (error) {
      console.error("Failed to delete ROI", error);
    }
  };

  const handleCameraChange = async (e) => {
    const id = e.target.value;
    try {
      // Connect stream in backend if needed without disconnecting other cameras
      await cameraService.connect(id);
      setActiveCameraId(id);
      fetchCameras();
    } catch (error) {
      console.error("Failed to switch camera", error);
    }
  };

  const activeCam = cameras.find(c => c.id === activeCameraId);
  const filteredRois = rois.filter(r => !r.cameraId || r.cameraId === activeCameraId);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Live Monitoring</h1>
        
        <div className="flex items-center gap-2">
          <Camera className="h-5 w-5 text-muted-foreground" />
          <select 
            className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background font-medium"
            value={activeCameraId || ''}
            onChange={handleCameraChange}
          >
            <option value="" disabled>Select Camera...</option>
            {cameras.map(cam => (
              <option key={cam.id} value={cam.id}>{cam.cameraName} ({cam.cameraType})</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column - Live Stream with Dynamic React Key & WebSocket */}
        <div className="lg:col-span-2 space-y-4">
          <LiveStreamViewer
            key={activeCameraId || 'default'}
            cameraId={activeCameraId}
            cameraName={activeCam?.cameraName}
            cameraStatus={stats.rawStatus}
            errorReason={stats.errorReason}
            isLocal={stats.isLocal || (activeCam?.cameraType === 'Laptop Webcam')}
            rois={rois}
            currentRect={currentRect}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onRetryCamera={async () => {
              if (activeCameraId) {
                await cameraService.connect(activeCameraId);
                fetchMetrics();
              }
            }}
          />
          
          <div className="flex justify-between items-center bg-card p-4 rounded-lg border">
            <div>
              <h3 className="font-medium">Interactive ROI Canvas</h3>
              <p className="text-xs text-muted-foreground">Draw rectangles directly on the feed to create detection zones.</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setCurrentRect(null)} disabled={!currentRect}>Clear Drawing</Button>
              <Button onClick={handleSaveRoi} disabled={!currentRect}>Save Drawn ROI</Button>
            </div>
          </div>
        </div>

        {/* Right Column - Stats & ROI List */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Activity className="h-4 w-4" /> Real-time Performance Metrics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Status</span>
                <span className="font-medium text-green-500">{stats.status}</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Active Camera</span>
                <span className="font-medium">
                  {activeCam?.cameraName || 'Default Webcam'}
                </span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Capture FPS</span>
                <span className="font-medium text-blue-500">{stats.captureFps || 30} FPS</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Detection FPS</span>
                <span className="font-medium text-purple-500">{stats.detectionFps || 0} FPS</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Frame Age (Latency)</span>
                <span className="font-medium text-green-500">{stats.frameAgeMs || 0} ms</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">YOLO Inference Time</span>
                <span className="font-medium">{stats.inferenceTimeMs || 0} ms</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Active ROIs</span>
                <span className="font-medium">{filteredRois.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Latest Event</span>
                <span className="font-medium text-xs">
                  {stats.latestDetection !== 'None' ? new Date(stats.latestDetection).toLocaleTimeString() : 'None'}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Map className="h-4 w-4" /> Configured ROIs ({activeCam?.cameraName || 'Active Camera'})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {filteredRois.length === 0 ? (
                <p className="text-sm text-muted-foreground">No ROIs configured for this camera.</p>
              ) : (
                <ul className="space-y-3">
                  {filteredRois.map(roi => (
                    <li key={roi._id || roi.id} className="flex items-center justify-between bg-secondary/50 p-2 rounded-md border">
                      <span className="text-sm font-medium">{roi.zoneName}</span>
                      <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => handleDeleteRoi(roi._id || roi.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Bottom - Recent Events */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" /> Recent Intrusion Events
          </CardTitle>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">No recent events.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
              {events.map(event => {
                const eventId = event._id || event.id;
                const snapshotUrl = event.snapshot 
                  ? (event.snapshot.startsWith('http') ? event.snapshot : `http://localhost:8000${event.snapshot}`)
                  : null;
                return (
                  <div key={eventId} className="flex flex-col border rounded-lg overflow-hidden bg-secondary/20">
                    <div className="h-32 bg-black relative">
                      {snapshotUrl ? (
                        <EventSnapshotImage 
                          src={snapshotUrl} 
                          alt="Snapshot" 
                          className="w-full h-full object-cover" 
                          containerClassName="w-full h-full p-1 text-[10px]"
                          showPlaceholderDetails={false}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-muted-foreground">No Image</div>
                      )}
                      <div className="absolute top-2 left-2 bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-sm">
                        {event.eventType || 'Intrusion'}
                      </div>
                    </div>
                    <div className="p-3">
                      <p className="text-xs font-semibold text-blue-500 truncate">{event.cameraName || event.cameraId || 'Camera'}</p>
                      <p className="text-xs font-medium truncate">ROI: {event.roiName || 'Detection Zone'}</p>
                      <p className="text-[10px] text-muted-foreground mt-1">
                        {new Date(event.timestamp).toLocaleString()}
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        Confidence: {(Number(event.confidence || 0) * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
