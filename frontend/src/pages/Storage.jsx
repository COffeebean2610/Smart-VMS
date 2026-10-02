import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Database, HardDrive, Video, Image as ImageIcon, Clock } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function Storage() {
  const [storageData, setStorageData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStorage = async () => {
      try {
        const response = await axios.get('http://localhost:8000/api/storage');
        setStorageData(response.data);
      } catch (error) {
        console.error("Failed to fetch storage data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchStorage();
  }, []);

  if (loading || !storageData) {
    return <div className="flex h-full items-center justify-center animate-pulse">Loading Storage Analytics...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Storage Management</h1>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Used Space</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{storageData.usedGB} GB</div>
            <p className="text-xs text-muted-foreground">{storageData.usedPercent}% of {storageData.totalGB} GB</p>
            <div className="mt-4 h-2 w-full bg-secondary rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary" 
                style={{ width: `${storageData.usedPercent}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Remaining Space</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{storageData.freeGB} GB</div>
            <p className="text-xs text-muted-foreground">Available capacity</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Retention Window</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {storageData.oldestRecording ? new Date(storageData.oldestRecording).toLocaleDateString() : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">Oldest Recording Available</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Storage Trend (Last 7 Days)</CardTitle>
          </CardHeader>
          <CardContent className="h-75">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={storageData.trend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="day" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))' }} />
                <Area type="monotone" dataKey="gb" stroke="hsl(var(--primary))" fillOpacity={0.3} fill="hsl(var(--primary))" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Content Distribution</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-lg border">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 text-blue-500 rounded-md">
                  <Video className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium">Recordings</p>
                  <p className="text-xs text-muted-foreground">MP4 Video Files</p>
                </div>
              </div>
              <div className="text-xl font-bold">{storageData.numRecordings}</div>
            </div>

            <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-lg border">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/20 text-green-500 rounded-md">
                  <ImageIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium">Snapshots</p>
                  <p className="text-xs text-muted-foreground">JPG Image Files</p>
                </div>
              </div>
              <div className="text-xl font-bold">{storageData.numSnapshots}</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
