import React, { useState, useEffect } from 'react';
import { eventService } from '../services/eventService';
import { recordingService } from '../services/recordingService';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Search, Play, Image as ImageIcon, Download, Trash2 } from 'lucide-react';
import VideoPlayer from '../components/video/VideoPlayer';
import EventSnapshotImage from '../components/EventSnapshotImage';

export default function Events() {
  const [events, setEvents] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Modals
  const [previewImage, setPreviewImage] = useState(null);
  const [activeEvent, setActiveEvent] = useState(null);

  const fetchEvents = async () => {
    try {
      const data = await eventService.getAll();
      setEvents(data);
    } catch {
      console.error("Failed to fetch events");
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleViewRecording = (event) => {
    setActiveEvent(event);
  };

  const filteredEvents = events.filter(e => 
    e.eventType.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.cameraId.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleExportCSV = () => {
    const headers = ['Timestamp', 'Camera ID', 'Event Type', 'ROI Name', 'Confidence', 'Status'];
    const csvContent = [
      headers.join(','),
      ...filteredEvents.map(e => [
        new Date(e.timestamp).toISOString(),
        e.cameraId,
        e.eventType,
        e.roiName || '',
        e.confidence,
        e.status || ''
      ].map(field => `"${field}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `events_export_${new Date().getTime()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDeleteEvent = async (id) => {
    if (!confirm("Are you sure you want to delete this event? This will delete the snapshot physically.")) return;
    try {
      await eventService.delete(id);
      setEvents(events.filter(e => (e.id || e._id) !== id));
    } catch (error) {
      console.error("Failed to delete event", error);
      alert("Failed to delete event");
    }
  };

  const handleBulkDelete = async (e) => {
    const filterType = e.target.value;
    if (!filterType) return;
    
    if (!confirm(`Are you sure you want to bulk delete events (${filterType})? This cannot be undone.`)) {
      e.target.value = ""; // Reset dropdown
      return;
    }
    
    try {
      const res = await eventService.bulkDelete(filterType);
      alert(`Deleted ${res.deletedRecords} records and ${res.deletedFiles} files.`);
      fetchEvents(); // Refresh list
    } catch (error) {
      console.error("Bulk delete failed", error);
      alert("Bulk delete failed");
    }
    e.target.value = "";
  };

  const handleDownloadSnapshot = async (event) => {
    if (!event.snapshot) return;
    const url = event.snapshot.startsWith('http') ? event.snapshot : `http://localhost:8000${event.snapshot}`;
    try {
      const resp = await fetch(url, { method: 'HEAD' });
      if (!resp.ok) {
        alert("This snapshot is not available on this device.");
        return;
      }
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `snapshot_${event.cameraId}_${new Date(event.timestamp).getTime()}.jpg`);
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch {
      alert("This snapshot is not available on this device.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Recent Events</h1>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Event Log</CardTitle>
            <div className="flex items-center gap-4">
              <div className="relative w-64">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Search events..." 
                  className="pl-8" 
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                />
              </div>
              
              <select 
                className="flex h-9 items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                onChange={handleBulkDelete}
                defaultValue=""
              >
                <option value="" disabled>Bulk Delete...</option>
                <option value="all">All Events</option>
                <option value="month">Older than 1 Month</option>
                <option value="week">Older than 1 Week</option>
                <option value="day">Older than 1 Day</option>
              </select>

              <Button variant="outline" onClick={handleExportCSV} className="gap-2">
                <Download className="h-4 w-4" /> Export CSV
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Camera ID</TableHead>
                <TableHead>ROI / Event</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Snapshot</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredEvents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No events found.
                  </TableCell>
                </TableRow>
              ) : (
                filteredEvents.map((event) => {
                  const eventId = event._id || event.id;
                  const snapshotUrl = event.snapshot
                    ? (event.snapshot.startsWith('http') ? event.snapshot : `http://localhost:8000${event.snapshot}`)
                    : null;
                  return (
                    <TableRow key={eventId}>
                      <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                      <TableCell className="font-mono text-xs">{event.cameraName || event.cameraId}</TableCell>
                      <TableCell className="font-medium">
                        <span className="capitalize">{event.eventType}</span>
                        {event.roiName && <div className="text-xs text-muted-foreground">ROI: {event.roiName}</div>}
                      </TableCell>
                      <TableCell>{(Number(event.confidence || 0) * 100).toFixed(1)}%</TableCell>
                      <TableCell>
                        {snapshotUrl ? (
                          <div className="flex items-center gap-2">
                            <div 
                              className="w-28 h-16 rounded border border-border overflow-hidden flex-shrink-0 cursor-pointer" 
                              onClick={() => setPreviewImage(snapshotUrl)}
                            >
                              <EventSnapshotImage 
                                src={snapshotUrl} 
                                alt="Snapshot" 
                                className="w-full h-full object-cover" 
                                containerClassName="w-full h-full p-1 text-[10px]"
                                showPlaceholderDetails={false}
                              />
                            </div>
                            <Button variant="ghost" size="sm" onClick={() => handleDownloadSnapshot(event)}>
                              <Download className="h-4 w-4 text-muted-foreground" />
                            </Button>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">No Image</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          {(event.recordingId || event.videoPath) && (
                            <Button size="sm" variant="outline" onClick={() => handleViewRecording(event)}>
                              <Play className="h-4 w-4 mr-1" /> Play
                            </Button>
                          )}
                          <Button size="sm" variant="destructive" onClick={() => handleDeleteEvent(eventId)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Snapshot Preview Modal */}
      <Dialog open={!!previewImage} onOpenChange={() => setPreviewImage(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Snapshot Preview</DialogTitle>
          </DialogHeader>
          <div className="flex justify-center bg-black/5 rounded-lg p-2 min-h-[250px]">
            {previewImage && (
              <EventSnapshotImage 
                src={previewImage} 
                alt="Snapshot Preview" 
                className="max-h-[60vh] object-contain rounded" 
                containerClassName="w-full h-64"
                showPlaceholderDetails={true}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Video Player Modal */}
      <Dialog open={!!activeEvent} onOpenChange={() => setActiveEvent(null)}>
        <DialogContent className="max-w-4xl p-0 overflow-hidden bg-black/95 border-none">
          <DialogHeader className="p-4 bg-background/80 backdrop-blur absolute top-0 w-full z-10 border-b">
            <DialogTitle>Event Playback: {activeEvent && new Date(activeEvent.timestamp).toLocaleString()}</DialogTitle>
          </DialogHeader>
          <div className="pt-14 pb-2 px-2 h-full">
            {activeEvent && (
              <VideoPlayer 
                url={activeEvent.recordingId 
                  ? recordingService.getStreamUrl(activeEvent.recordingId)
                  : (activeEvent.videoPath ? `http://localhost:8000${activeEvent.videoPath}` : '')} 
                events={[activeEvent]}
                autoSeekTime={activeEvent.videoTimestamp || 0}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
