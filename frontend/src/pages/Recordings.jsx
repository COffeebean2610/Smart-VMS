import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { recordingService } from '../services/recordingService';
import { eventService } from '../services/eventService';
import VideoPlayer from '../components/video/VideoPlayer';
import { Search, Play, Download, Trash2, Video } from 'lucide-react';

export default function Recordings() {
  const [recordings, setRecordings] = useState([]);
  const [events, setEvents] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeRecording, setActiveRecording] = useState(null);
  const [isPlayerOpen, setIsPlayerOpen] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const recs = await recordingService.getAll();
      setRecordings(recs);
      
      const evs = await eventService.getAll();
      setEvents(evs);
    } catch (error) {
      console.error("Failed to fetch recordings:", error);
    }
  };

  const formatDuration = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handlePlay = (recording) => {
    setActiveRecording(recording);
    setIsPlayerOpen(true);
  };

  // Filter events belonging to the active recording
  const activeEvents = activeRecording 
    ? events.filter(e => e.recordingId === activeRecording.id) 
    : [];

  const filteredRecordings = recordings.filter(rec => 
    rec.cameraId.toLowerCase().includes(searchTerm.toLowerCase()) || 
    new Date(rec.startTime).toLocaleDateString().includes(searchTerm)
  );

  const handleExportCSV = () => {
    const headers = ['Camera ID', 'Start Time', 'Duration (seconds)', 'File Size (bytes)', 'File Path'];
    const csvContent = [
      headers.join(','),
      ...filteredRecordings.map(r => [
        r.cameraId,
        new Date(r.startTime).toISOString(),
        r.duration,
        r.fileSize,
        r.filePath
      ].map(field => `"${field}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `recordings_export_${new Date().getTime()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDeleteRecording = async (id) => {
    if (!confirm("Are you sure you want to delete this recording? This will permanently delete the MP4 file from storage.")) return;
    try {
      await recordingService.delete(id);
      setRecordings(recordings.filter(r => r.id !== id));
    } catch (error) {
      console.error("Failed to delete recording", error);
      alert("Failed to delete recording");
    }
  };

  const handleBulkDelete = async (e) => {
    const filterType = e.target.value;
    if (!filterType) return;
    
    if (!confirm(`Are you sure you want to bulk delete recordings (${filterType})? This cannot be undone.`)) {
      e.target.value = "";
      return;
    }
    
    try {
      const res = await recordingService.bulkDelete(filterType);
      alert(`Deleted ${res.deletedRecords} database records and ${res.deletedFiles} MP4 files.`);
      fetchData();
    } catch (error) {
      console.error("Bulk delete failed", error);
      alert("Bulk delete failed");
    }
    e.target.value = "";
  };

  const handleDownloadRecording = (recording) => {
    if (!recording.id) return;
    const link = document.createElement('a');
    link.href = recordingService.getStreamUrl(recording.id); // Triggers download prompt for MP4
    link.setAttribute('download', `recording_${recording.cameraId}_${new Date(recording.startTime).getTime()}.mp4`);
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Recordings</h1>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Video className="h-5 w-5" /> Recording Browser
          </CardTitle>
          <div className="flex items-center gap-4">
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search by camera or date..."
                className="pl-8"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            
            <select 
              className="flex h-9 items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              onChange={handleBulkDelete}
              defaultValue=""
            >
              <option value="" disabled>Bulk Delete...</option>
              <option value="all">All Recordings</option>
              <option value="month">Older than 1 Month</option>
              <option value="week">Older than 1 Week</option>
              <option value="day">Older than 1 Day</option>
            </select>

            <Button variant="outline" onClick={handleExportCSV} className="gap-2">
              <Download className="h-4 w-4" /> Export CSV
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Camera</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Start Time</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Size</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRecordings.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">
                    No recordings found.
                  </TableCell>
                </TableRow>
              ) : (
                filteredRecordings.map((rec) => (
                  <TableRow key={rec.id}>
                    <TableCell className="font-medium">{rec.cameraId}</TableCell>
                    <TableCell>
                      <span className="px-2 py-0.5 rounded text-xs bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 font-medium">
                        {rec.type || 'Intrusion Event'}
                      </span>
                    </TableCell>
                    <TableCell>{new Date(rec.startTime).toLocaleString()}</TableCell>
                    <TableCell>{formatDuration(rec.duration)}</TableCell>
                    <TableCell>{formatSize(rec.fileSize)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" size="sm" onClick={() => handlePlay(rec)}>
                          <Play className="h-4 w-4 mr-1" /> Play
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDownloadRecording(rec)} className="h-8 w-8 text-muted-foreground hover:text-foreground">
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDeleteRecording(rec.id)} className="h-8 w-8 text-destructive hover:bg-destructive/10">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Video Player Modal */}
      <Dialog open={isPlayerOpen} onOpenChange={setIsPlayerOpen}>
        <DialogContent className="max-w-4xl p-0 overflow-hidden bg-black/95 border-none">
          <DialogHeader className="p-4 bg-background/80 backdrop-blur absolute top-0 w-full z-10 border-b">
            <DialogTitle>Playback: {activeRecording?.cameraId} - {activeRecording ? new Date(activeRecording.startTime).toLocaleString() : ''}</DialogTitle>
          </DialogHeader>
          <div className="pt-14 pb-2 px-2 h-full">
            {activeRecording && (
              <VideoPlayer 
                url={recordingService.getStreamUrl(activeRecording.id)} 
                events={activeEvents}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
