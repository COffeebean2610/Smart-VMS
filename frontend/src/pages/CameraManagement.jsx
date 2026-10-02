import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { cameraService } from '../services/cameraService';
import { Plus, Trash2, Video, CheckCircle, XCircle, Loader2, Play } from 'lucide-react';

export default function CameraManagement() {
  const [cameras, setCameras] = useState([]);
  const [isAddOpen, setIsAddOpen] = useState(false);
  
  // Form state
  const [cameraName, setCameraName] = useState('');
  const [cameraType, setCameraType] = useState('Laptop Webcam');
  const [streamUrl, setStreamUrl] = useState('');
  const [location, setLocation] = useState('');
  const [description, setDescription] = useState('');
  
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState(null); // null, 'success', 'failed'
  const [testData, setTestData] = useState(null);

  useEffect(() => {
    fetchCameras();
  }, []);

  const fetchCameras = async () => {
    try {
      const data = await cameraService.getAll();
      setCameras(data);
    } catch (error) {
      console.error("Failed to fetch cameras", error);
    }
  };

  const resetForm = () => {
    setCameraName('');
    setCameraType('Laptop Webcam');
    setStreamUrl('');
    setLocation('');
    setDescription('');
    setTestResult(null);
    setTestData(null);
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const urlToTest = cameraType === 'Laptop Webcam' ? '0' : streamUrl;
      const res = await cameraService.testConnection(urlToTest);
      if (res.status === 'success') {
        setTestResult('success');
        setTestData({ fps: res.fps, resolution: res.resolution });
      } else if (res.errorReason === 'camera_blocked') {
        setTestResult('camera_blocked');
      } else {
        setTestResult('failed');
      }
    } catch (error) {
      console.error("Test failed", error);
      setTestResult('failed');
    }
    setIsTesting(false);
  };

  const handleSave = async () => {
    try {
      await cameraService.create({
        cameraName,
        cameraType,
        streamUrl: cameraType === 'Laptop Webcam' ? '0' : streamUrl,
        location,
        description
      });
      setIsAddOpen(false);
      resetForm();
      fetchCameras();
    } catch (error) {
      console.error("Failed to save camera", error);
    }
  };

  const handleDelete = async (id) => {
    if (confirm("Delete this camera?")) {
      try {
        await cameraService.delete(id);
        fetchCameras();
      } catch (error) {
        console.error("Failed to delete camera", error);
      }
    }
  };

  const handleConnect = async (id) => {
    try {
      await cameraService.connect(id);
      fetchCameras();
      alert("Successfully switched active camera stream!");
    } catch (error) {
      console.error("Failed to connect camera", error);
      alert("Failed to connect camera");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Camera Management</h1>
        <Button onClick={() => { resetForm(); setIsAddOpen(true); }} className="gap-2">
          <Plus className="h-4 w-4" /> Add Camera
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Available Cameras</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Camera Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Resolution</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {cameras.map((cam) => (
                <TableRow key={cam.id}>
                  <TableCell className="font-medium">{cam.cameraName}</TableCell>
                  <TableCell>{cam.cameraType}</TableCell>
                  <TableCell>{cam.location}</TableCell>
                  <TableCell>
                    {cam.status === 'online' ? (
                      <span className="flex items-center gap-2 text-green-500 font-medium">
                        <Video className="h-4 w-4" /> Active
                      </span>
                    ) : (
                      <span className="flex items-center gap-2 text-muted-foreground font-medium">
                        <Video className="h-4 w-4" /> Offline
                      </span>
                    )}
                  </TableCell>
                  <TableCell>{cam.resolution}</TableCell>
                  <TableCell className="text-right flex items-center justify-end gap-2">
                    {cam.status !== 'online' && (
                      <Button variant="outline" size="sm" onClick={() => handleConnect(cam.id)} className="gap-2">
                        <Play className="h-4 w-4" /> Connect
                      </Button>
                    )}
                    <Button variant="destructive" size="icon" onClick={() => handleDelete(cam.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add New Camera</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Camera Name</label>
              <Input value={cameraName} onChange={e => setCameraName(e.target.value)} placeholder="e.g. Main Lobby" />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Camera Type</label>
              <select 
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                value={cameraType}
                onChange={e => setCameraType(e.target.value)}
              >
                <option value="Laptop Webcam">Laptop Webcam</option>
                <option value="HTTP Camera">HTTP Camera</option>
                <option value="HTTPS Camera">HTTPS Camera</option>
                <option value="RTSP Camera">RTSP Camera</option>
              </select>
            </div>

            {cameraType !== 'Laptop Webcam' && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Stream URL</label>
                <Input value={streamUrl} onChange={e => setStreamUrl(e.target.value)} placeholder="rtsp://username:password@192.168.1.100:554/stream" />
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Location</label>
              <Input value={location} onChange={e => setLocation(e.target.value)} placeholder="e.g. Building A" />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Description (Optional)</label>
              <Input value={description} onChange={e => setDescription(e.target.value)} placeholder="..." />
            </div>

            <div className="flex flex-col gap-2 pt-2 border-t border-border">
              <Button variant="secondary" onClick={handleTestConnection} disabled={isTesting}>
                {isTesting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                {isTesting ? "Testing Connection..." : "Test Connection"}
              </Button>
              
              {testResult === 'success' && (
                <div className="p-3 bg-green-500/10 border border-green-500/20 text-green-500 rounded-md flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 mt-0.5" />
                  <div>
                    <p className="font-medium text-sm">Connection Successful</p>
                    <p className="text-xs mt-1">Resolution: {testData?.resolution}</p>
                    <p className="text-xs">FPS: {testData?.fps}</p>
                  </div>
                </div>
              )}
              
              {testResult === 'camera_blocked' && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-500 rounded-md space-y-2">
                  <div className="flex items-start gap-2">
                    <XCircle className="h-5 w-5 mt-0.5 shrink-0" />
                    <div>
                      <p className="font-semibold text-sm">Camera Access Blocked by Windows</p>
                      <p className="text-xs mt-1 leading-relaxed">
                        Camera access is blocked by Windows. Please enable Camera access for desktop apps in Windows Settings.
                      </p>
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full text-xs"
                    onClick={() => { window.location.href = 'ms-settings:privacy-webcam'; }}
                  >
                    Open Windows Settings
                  </Button>
                </div>
              )}

              {testResult === 'failed' && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-500 rounded-md flex items-start gap-2">
                  <XCircle className="h-5 w-5 mt-0.5" />
                  <div>
                    <p className="font-medium text-sm">Connection Failed</p>
                    <p className="text-xs mt-1">Check the URL or ensure the camera is reachable.</p>
                  </div>
                </div>
              )}
            </div>

          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button variant="outline" onClick={() => setIsAddOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={!cameraName || (cameraType !== 'Laptop Webcam' && !streamUrl)}>Save Camera</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
