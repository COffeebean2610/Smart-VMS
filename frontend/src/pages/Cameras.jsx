import { useState, useEffect } from 'react';
import { cameraService } from '../services/cameraService';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '../components/ui/table';
import { Cctv, Plus, Edit, Trash2 } from 'lucide-react';

export default function Cameras() {
  const [cameras, setCameras] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [currentCamera, setCurrentCamera] = useState({ cameraName: '', location: '', streamSource: '' });
  const [isEditing, setIsEditing] = useState(false);

  const fetchCameras = async () => {
    try {
      const data = await cameraService.getAll();
      setCameras(data);
    } catch {
      console.error("Failed to fetch cameras");
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const handleSave = async () => {
    try {
      if (isEditing) {
        await cameraService.update(currentCamera._id, currentCamera);
      } else {
        await cameraService.create(currentCamera);
      }
      setIsDialogOpen(false);
      fetchCameras();
    } catch {
      console.error("Failed to save camera");
    }
  };

  const handleDelete = async (id) => {
    if(confirm("Are you sure you want to delete this camera?")) {
      try {
        await cameraService.delete(id);
        fetchCameras();
      } catch {
        console.error("Failed to delete camera");
      }
    }
  };

  const openNewDialog = () => {
    setCurrentCamera({ cameraName: '', location: '', streamSource: '' });
    setIsEditing(false);
    setIsDialogOpen(true);
  };

  const openEditDialog = (camera) => {
    setCurrentCamera(camera);
    setIsEditing(true);
    setIsDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Cameras Management</h1>
        <Button onClick={openNewDialog}><Plus className="mr-2 h-4 w-4" /> Add Camera</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Camera List</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {cameras.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    No cameras found. Add one to get started.
                  </TableCell>
                </TableRow>
              ) : (
                cameras.map((cam) => (
                  <TableRow key={cam._id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Cctv className="h-4 w-4 text-muted-foreground" />
                        {cam.cameraName}
                      </div>
                    </TableCell>
                    <TableCell>{cam.location}</TableCell>
                    <TableCell className="max-w-50 truncate">{cam.streamSource}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${cam.status === 'online' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                        {cam.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => openEditDialog(cam)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleDelete(cam._id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Camera" : "Add New Camera"}</DialogTitle>
          <DialogDescription>
            {isEditing ? "Update the details for this camera." : "Enter the connection details for the new camera."}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <label className="text-sm font-medium">Camera Name</label>
            <Input 
              value={currentCamera.cameraName} 
              onChange={e => setCurrentCamera({...currentCamera, cameraName: e.target.value})} 
              placeholder="e.g. Front Entrance" 
            />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Location</label>
            <Input 
              value={currentCamera.location} 
              onChange={e => setCurrentCamera({...currentCamera, location: e.target.value})} 
              placeholder="e.g. Lobby" 
            />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Stream Source URL</label>
            <Input 
              value={currentCamera.streamSource} 
              onChange={e => setCurrentCamera({...currentCamera, streamSource: e.target.value})} 
              placeholder="rtsp://..." 
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave}>Save</Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
