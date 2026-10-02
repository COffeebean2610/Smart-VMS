import { useState, useEffect } from 'react';
import { roiService } from '../services/roiService';
import { cameraService } from '../services/cameraService';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '../components/ui/table';
import { Map, Plus, Edit, Trash2 } from 'lucide-react';

export default function DetectionZones() {
  const [zones, setZones] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [currentZone, setCurrentZone] = useState({ zoneName: '', cameraId: '', coordinates: [] });
  const [isEditing, setIsEditing] = useState(false);

  const fetchData = async () => {
    try {
      const zData = await roiService.getAll();
      const cData = await cameraService.getAll();
      setZones(zData);
      setCameras(cData);
    } catch {
      console.error("Failed to fetch data");
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSave = async () => {
    try {
      if (isEditing) {
        await roiService.update(currentZone._id, currentZone);
      } else {
        await roiService.create(currentZone);
      }
      setIsDialogOpen(false);
      fetchData();
    } catch {
      console.error("Failed to save zone");
    }
  };

  const handleDelete = async (id) => {
    if(confirm("Are you sure you want to delete this zone?")) {
      try {
        await roiService.delete(id);
        fetchData();
      } catch {
        console.error("Failed to delete zone");
      }
    }
  };

  const openNewDialog = () => {
    setCurrentZone({ zoneName: '', cameraId: '', coordinates: [] });
    setIsEditing(false);
    setIsDialogOpen(true);
  };

  const openEditDialog = (zone) => {
    setCurrentZone(zone);
    setIsEditing(true);
    setIsDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Detection Zones</h1>
        <Button onClick={openNewDialog}><Plus className="mr-2 h-4 w-4" /> Add Zone</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Configured Zones</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Zone Name</TableHead>
                <TableHead>Camera</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {zones.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                    No detection zones found. Add one to start monitoring.
                  </TableCell>
                </TableRow>
              ) : (
                zones.map((zone) => (
                  <TableRow key={zone._id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Map className="h-4 w-4 text-muted-foreground" />
                        {zone.zoneName}
                      </div>
                    </TableCell>
                    <TableCell>{cameras.find(c => c._id === zone.cameraId)?.cameraName || 'Unknown Camera'}</TableCell>
                    <TableCell>{new Date(zone.createdAt).toLocaleDateString()}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => openEditDialog(zone)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleDelete(zone._id)}>
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
          <DialogTitle>{isEditing ? "Edit Zone" : "Add New Zone"}</DialogTitle>
          <DialogDescription>
            Configure metadata for the detection zone (Canvas drawing available in future phase).
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <label className="text-sm font-medium">Zone Name</label>
            <Input 
              value={currentZone.zoneName} 
              onChange={e => setCurrentZone({...currentZone, zoneName: e.target.value})} 
              placeholder="e.g. Lobby Entrance" 
            />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Select Camera</label>
            <select 
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={currentZone.cameraId}
              onChange={e => setCurrentZone({...currentZone, cameraId: e.target.value})}
            >
              <option value="">Select a camera...</option>
              {cameras.map(cam => (
                <option key={cam._id} value={cam._id}>{cam.cameraName}</option>
              ))}
            </select>
          </div>
          <div className="p-4 rounded border bg-secondary/50 text-xs text-muted-foreground text-center">
            Coordinate drawing interface will be implemented in Phase 2.
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} disabled={!currentZone.cameraId || !currentZone.zoneName}>Save Zone</Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
