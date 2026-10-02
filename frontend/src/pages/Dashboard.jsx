import React, { useEffect, useState } from 'react';
import { dashboardService } from '../services/dashboardService';
import { eventService } from '../services/eventService';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Cctv, AlertTriangle, Video, Activity, Target } from 'lucide-react';
import { 
  LineChart, Line, PieChart, Pie, Cell, AreaChart, Area, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [charts, setCharts] = useState(null);
  const [latestEvents, setLatestEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      const [summaryData, chartsData, eventsData] = await Promise.all([
        dashboardService.getSummary(),
        dashboardService.getCharts(),
        eventService.getAll()
      ]);
      setSummary(summaryData);
      setCharts(chartsData);
      setLatestEvents(eventsData.slice(0, 5)); // Top 5 alerts
    } catch (error) {
      console.error("Failed to load dashboard data", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000); // Live refresh
    return () => clearInterval(interval);
  }, []);

  if (loading || !summary || !charts) {
    return <div className="flex h-full items-center justify-center animate-pulse">Loading Analytics...</div>;
  }

  const COLORS = ['hsl(var(--primary))', '#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

  return (
    <div className="space-y-6 pb-10">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h1>
        <div className="flex items-center gap-2 text-sm text-green-500 bg-green-500/10 px-3 py-1 rounded-full font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </span>
          Live Monitoring
        </div>
      </div>
      
      {/* Top Stats Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="shadow-sm border-0 bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="flex flex-col">
              <CardTitle className="text-sm font-semibold text-muted-foreground">Camera Network</CardTitle>
              <div className="text-3xl font-bold mt-2">{summary.onlineCameras} / {summary.totalCameras}</div>
            </div>
            <div className="h-12 w-12 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <Cctv className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-blue-600 font-medium">{summary.offlineCameras} cameras offline</p>
          </CardContent>
        </Card>
        
        <Card className="shadow-sm border-0 bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="flex flex-col">
              <CardTitle className="text-sm font-semibold text-muted-foreground">Today's Intrusions</CardTitle>
              <div className="text-3xl font-bold mt-2 text-red-600">{summary.intrusionsToday}</div>
            </div>
            <div className="h-12 w-12 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-red-600 font-medium flex items-center">
               ↑ 28% <span className="text-muted-foreground ml-1 font-normal">vs yesterday</span>
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-0 bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="flex flex-col">
              <CardTitle className="text-sm font-semibold text-muted-foreground">AI Accuracy</CardTitle>
              <div className="text-3xl font-bold mt-2">{summary.averageConfidence}%</div>
            </div>
            <div className="h-12 w-12 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <Target className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-green-600 font-medium flex items-center">
              ↑ 5.6% <span className="text-muted-foreground ml-1 font-normal">vs yesterday</span>
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-0 bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="flex flex-col">
              <CardTitle className="text-sm font-semibold text-muted-foreground">Recordings Stored</CardTitle>
              <div className="text-3xl font-bold mt-2">{summary.recordingsStored}</div>
            </div>
            <div className="h-12 w-12 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
              <Video className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-purple-600 font-medium">
              {summary.storageUsedGB} GB Used <span className="text-muted-foreground font-normal">({summary.storageUsedPercent}%)</span>
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* 1. Events Per Hour */}
        <Card className="lg:col-span-2 shadow-sm border-0">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-blue-100 flex items-center justify-center">
                <Activity className="h-3 w-3 text-blue-600" />
              </div>
              Events Per Hour (Today)
            </CardTitle>
            <div className="text-sm font-medium border px-3 py-1 rounded-md text-muted-foreground">Today ▾</div>
          </CardHeader>
          <CardContent className="h-72 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={charts.eventsPerHour} margin={{ top: 5, right: 20, bottom: 5, left: -20 }}>
                <defs>
                  <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted" />
                <XAxis dataKey="hour" axisLine={false} tickLine={false} className="text-xs text-muted-foreground" />
                <YAxis axisLine={false} tickLine={false} className="text-xs text-muted-foreground" />
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                <Line type="monotone" dataKey="events" stroke="#3b82f6" strokeWidth={3} dot={{r: 4, strokeWidth: 2, fill: 'white'}} activeDot={{r: 6}} />
                {/* Simulated Area underneath the line chart for aesthetics */}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* 4. Detection Distribution */}
        <Card className="shadow-sm border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-indigo-100 flex items-center justify-center">
                <PieChart className="h-3 w-3 text-indigo-600" />
              </div>
              Event Types
            </CardTitle>
          </CardHeader>
          <CardContent className="h-72 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={charts.detectionDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  fill="#8884d8"
                  paddingAngle={2}
                  dataKey="value"
                >
                  {charts.detectionDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                <Legend layout="vertical" verticalAlign="middle" align="right" wrapperStyle={{ fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* 5. Weekly Intrusion Trend */}
        <Card className="shadow-sm border-0">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-lg font-bold">Weekly Trend</CardTitle>
            <div className="text-xs font-medium border px-2 py-1 rounded-md text-muted-foreground">This Week ▾</div>
          </CardHeader>
          <CardContent className="h-64 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={charts.weeklyTrend} margin={{ top: 5, right: 0, bottom: 5, left: -20 }}>
                <defs>
                  <linearGradient id="colorGreen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} className="text-xs text-muted-foreground" />
                <YAxis axisLine={false} tickLine={false} className="text-xs text-muted-foreground" />
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                <Area type="monotone" dataKey="intrusions" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorGreen)" dot={{r: 3, fill: 'white', strokeWidth: 2}} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* 2. Intrusions by Camera (Custom Progress Bars) */}
        <Card className="shadow-sm border-0">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Top Cameras (Intrusions)</CardTitle>
          </CardHeader>
          <CardContent className="h-64 flex flex-col justify-center gap-4">
            {charts.intrusionsByCamera.map((cam, idx) => {
              const max = charts.intrusionsByCamera[0]?.intrusions || 1;
              const percent = (cam.intrusions / max) * 100;
              return (
                <div key={idx} className="flex items-center gap-4">
                  <span className="text-sm font-semibold text-muted-foreground w-4">{idx + 1}</span>
                  <div className="flex-1">
                    <div className="flex justify-between mb-1">
                      <span className="text-sm font-medium">{cam.camera}</span>
                      <span className="text-sm font-medium">{cam.intrusions} <span className="text-xs text-muted-foreground ml-1">{Math.round(percent)}%</span></span>
                    </div>
                    <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-green-500 rounded-full" style={{ width: `${percent}%` }}></div>
                    </div>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* 3. Storage Usage Donut */}
        <Card className="shadow-sm border-0">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Storage Allocation</CardTitle>
          </CardHeader>
          <CardContent className="h-64 flex flex-row items-center justify-between">
            <div className="w-1/2 h-full relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={charts.storageUsage}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={75}
                    fill="#8884d8"
                    paddingAngle={0}
                    dataKey="value"
                    stroke="none"
                  >
                    <Cell fill="#3b82f6" />
                    <Cell fill="hsl(var(--secondary))" />
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-xl font-bold">{summary.storageUsedPercent}%</span>
                <span className="text-xs text-muted-foreground">Used</span>
              </div>
            </div>
            <div className="w-1/2 flex flex-col gap-3 pl-4 border-l">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground text-xs">Used Space</span>
                <span className="font-semibold text-blue-600">{summary.storageUsedGB} GB</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground text-xs">Total Space</span>
                <span className="font-semibold">{summary.storageTotalGB} GB</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground text-xs">Free Space</span>
                <span className="font-semibold text-green-600">{(summary.storageTotalGB - summary.storageUsedGB).toFixed(1)} GB</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Alert Panel */}
      <Card className="border-red-500/20 shadow-lg shadow-red-500/5">
        <CardHeader className="bg-red-500/5 border-b border-red-500/10">
          <CardTitle className="text-lg flex items-center gap-2 text-red-500">
            <Activity className="h-5 w-5" /> Live Alert Panel
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {latestEvents.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground">No recent alerts.</div>
          ) : (
            <div className="divide-y divide-border">
              {latestEvents.map((alert, idx) => (
                <div key={alert.id || idx} className={`p-4 flex items-center justify-between hover:bg-secondary/20 transition-colors ${idx === 0 ? 'bg-red-500/5' : ''}`}>
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-full bg-red-500/20 text-red-500 flex items-center justify-center">
                      <AlertTriangle className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-semibold text-sm">{alert.eventType}</p>
                      <p className="text-xs text-muted-foreground">{new Date(alert.timestamp).toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-8 text-sm">
                    <div className="hidden md:block">
                      <p className="text-muted-foreground text-xs">Camera</p>
                      <p className="font-medium">{alert.cameraId || 'default_cam_01'}</p>
                    </div>
                    <div className="hidden sm:block">
                      <p className="text-muted-foreground text-xs">Zone (ROI)</p>
                      <p className="font-medium">{alert.roiName}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">Confidence</p>
                      <p className="font-medium">{(alert.confidence * 100).toFixed(1)}%</p>
                    </div>
                    <div>
                      <span className="px-2 py-1 rounded text-xs font-semibold bg-red-500/10 text-red-500">
                        {alert.status || 'Active'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
