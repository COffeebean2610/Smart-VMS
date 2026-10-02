import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { 
  Database, 
  Bell, 
  Camera, 
  CheckCircle, 
  XCircle, 
  ArrowRight, 
  ArrowLeft, 
  ShieldCheck, 
  Send, 
  Save, 
  Cctv,
  Video,
  Sparkles
} from 'lucide-react';
import { saveDbConfig, completeFirstRun } from '../services/systemService';
import api from '../services/api';
import { cameraService } from '../services/cameraService';

export default function FirstRunWizard({ onComplete }) {
  const [step, setStep] = useState(1);

  // Step 1: MongoDB States
  const [mongoUri, setMongoUri] = useState('');
  const [isSavingDb, setIsSavingDb] = useState(false);
  const [dbResult, setDbResult] = useState(null);

  // Step 2: Telegram States
  const [telegramEnabled, setTelegramEnabled] = useState(true);
  const [botToken, setBotToken] = useState('');
  const [chatId, setChatId] = useState('');
  const [isSavingTelegram, setIsSavingTelegram] = useState(false);
  const [telegramResult, setTelegramResult] = useState(null);
  const [isTestingTelegram, setIsTestingTelegram] = useState(false);
  const [telegramTestResult, setTelegramTestResult] = useState(null);

  // Step 3: Camera States
  const [cameraName, setCameraName] = useState('Primary Camera');
  const [cameraType, setCameraType] = useState('Laptop Webcam');
  const [streamUrl, setStreamUrl] = useState('0');
  const [isTestingCamera, setIsTestingCamera] = useState(false);
  const [cameraTestResult, setCameraTestResult] = useState(null);
  const [isSavingCamera, setIsSavingCamera] = useState(false);
  const [cameraSaved, setCameraSaved] = useState(false);

  // Step 1 Handler: DB Save & Test
  const handleSaveDb = async (e) => {
    if (e) e.preventDefault();
    if (!mongoUri.trim()) {
      setDbResult({ type: 'error', message: 'Please enter a valid MongoDB Atlas connection string.' });
      return;
    }
    setIsSavingDb(true);
    setDbResult(null);
    try {
      const res = await saveDbConfig(mongoUri.trim());
      if (res.success) {
        setDbResult({ type: 'success', message: 'Connected to MongoDB Atlas securely!' });
      } else {
        setDbResult({ type: 'error', message: res.message || 'Unable to connect to MongoDB Atlas.' });
      }
    } catch (err) {
      setDbResult({ 
        type: 'error', 
        message: err.response?.data?.detail || 'Connection failed. Please check network and credentials.' 
      });
    } finally {
      setIsSavingDb(false);
    }
  };

  // Step 2 Handlers: Telegram
  const handleSaveTelegram = async (e) => {
    if (e) e.preventDefault();
    setIsSavingTelegram(true);
    setTelegramResult(null);
    try {
      const payload = {
        enabled: telegramEnabled,
        botToken: botToken.trim() ? botToken.trim() : undefined,
        chatId: chatId.trim(),
      };
      const res = await api.post('/notifications/telegram/config', payload);
      setTelegramResult({ type: 'success', message: res.data.message || 'Telegram configuration saved securely!' });
    } catch (err) {
      setTelegramResult({ 
        type: 'error', 
        message: err.response?.data?.detail || 'Failed to save Telegram configuration.' 
      });
    } finally {
      setIsSavingTelegram(false);
    }
  };

  const handleTestTelegram = async () => {
    setIsTestingTelegram(true);
    setTelegramTestResult(null);
    try {
      const res = await api.post('/notifications/telegram/test');
      if (res.data.success) {
        setTelegramTestResult({ type: 'success', message: res.data.message || 'Smart VMS Telegram test alert — connection successful.' });
      } else {
        setTelegramTestResult({ type: 'error', message: res.data.message || 'Failed to send Telegram test message.' });
      }
    } catch (err) {
      setTelegramTestResult({ 
        type: 'error', 
        message: err.response?.data?.message || 'Telegram test alert failed. Please verify credentials.' 
      });
    } finally {
      setIsTestingTelegram(false);
    }
  };

  // Step 3 Handlers: Camera
  const handleTestCamera = async () => {
    setIsTestingCamera(true);
    setCameraTestResult(null);
    try {
      const url = cameraType === 'Laptop Webcam' ? '0' : streamUrl.trim();
      const res = await cameraService.testConnection(url);
      if (res.status === 'success') {
        setCameraTestResult({ 
          type: 'success', 
          message: `Camera verified! FPS: ${res.fps}, Resolution: ${res.resolution}` 
        });
      } else if (res.errorReason === 'camera_blocked') {
        setCameraTestResult({ 
          type: 'blocked', 
          message: 'Camera access is blocked by Windows. Please enable Camera access for desktop apps in Windows Settings.' 
        });
      } else {
        setCameraTestResult({ type: 'error', message: res.message || 'Could not connect to camera stream.' });
      }
    } catch {
      setCameraTestResult({ type: 'error', message: 'Camera stream connection failed.' });
    } finally {
      setIsTestingCamera(false);
    }
  };

  const handleSaveCamera = async () => {
    setIsSavingCamera(true);
    try {
      const url = cameraType === 'Laptop Webcam' ? '0' : streamUrl.trim();
      await cameraService.create({
        cameraName,
        cameraType,
        streamUrl: url,
        location: 'Default Location',
        description: 'Added during initial setup',
      });
      setCameraSaved(true);
    } catch (err) {
      console.error("Camera save error:", err);
    } finally {
      setIsSavingCamera(false);
    }
  };


  // Step 4 Handler: Complete Setup
  const handleCompleteSetup = async () => {
    try {
      await completeFirstRun();
    } catch (e) {
      console.error("Error marking setup completed:", e);
    }
    if (onComplete) {
      onComplete();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
      <div className="w-full max-w-2xl bg-card border border-border rounded-xl shadow-2xl overflow-hidden my-auto">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-primary/20 via-primary/10 to-transparent p-6 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-primary/20 text-primary rounded-lg">
                <Cctv className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-xl font-bold tracking-tight">Smart VMS — Initial Setup Wizard</h2>
                <p className="text-xs text-muted-foreground">Welcome! Let's configure your system step-by-step.</p>
              </div>
            </div>
            <div className="text-xs font-semibold px-3 py-1 bg-primary/10 text-primary rounded-full border border-primary/20">
              Step {step} of 4
            </div>
          </div>

          {/* Stepper Progress Bar */}
          <div className="grid grid-cols-4 gap-2 mt-6">
            {[1, 2, 3, 4].map((i) => (
              <div 
                key={i} 
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  i <= step ? 'bg-primary' : 'bg-muted'
                }`} 
              />
            ))}
          </div>
        </div>

        {/* Step Contents */}
        <div className="p-6 space-y-6">
          
          {/* STEP 1: MongoDB Configuration */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-base font-semibold">
                <Database className="h-5 w-5 text-primary" /> Step 1: MongoDB Atlas Configuration
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Connect Smart VMS to your MongoDB Atlas cloud database. Connection details will be encrypted locally using Windows DPAPI.
              </p>

              <form onSubmit={handleSaveDb} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">MongoDB Atlas Connection String</label>
                  <Input
                    type="password"
                    placeholder="mongodb+srv://username:password@cluster.mongodb.net/smartvms"
                    value={mongoUri}
                    onChange={(e) => setMongoUri(e.target.value)}
                    className="font-mono text-xs"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Format: mongodb+srv://&lt;username&gt;:&lt;password&gt;@cluster...
                  </p>
                </div>

                <Button type="submit" disabled={isSavingDb} className="gap-2">
                  <Save className="h-4 w-4" />
                  {isSavingDb ? 'Testing & Saving...' : 'Save & Test Connection'}
                </Button>
              </form>

              {dbResult && (
                <div className={`flex items-center gap-2 p-3 rounded-md text-xs border ${
                  dbResult.type === 'success' 
                    ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800' 
                    : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
                }`}>
                  {dbResult.type === 'success' ? <CheckCircle className="h-4 w-4 shrink-0" /> : <XCircle className="h-4 w-4 shrink-0" />}
                  <span>{dbResult.message}</span>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: Telegram Configuration */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-base font-semibold">
                <Bell className="h-5 w-5 text-primary" /> Step 2: Telegram Intrusion Alerts
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Configure Telegram Bot credentials for instant intrusion notifications, snapshots, and video clips.
              </p>

              <div className="flex items-center justify-between p-3.5 rounded-lg bg-secondary/50 border">
                <div>
                  <p className="font-medium text-xs">Enable Telegram Alerts</p>
                  <p className="text-[11px] text-muted-foreground">Send real-time alerts upon zone intrusion</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={telegramEnabled} 
                    onChange={(e) => setTelegramEnabled(e.target.checked)}
                    className="sr-only peer" 
                  />
                  <div className="w-11 h-6 bg-muted peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>

              <form onSubmit={handleSaveTelegram} className="space-y-3">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold">Telegram Bot Token</label>
                    <Input
                      type="password"
                      placeholder="123456789:ABCdef..."
                      value={botToken}
                      onChange={(e) => setBotToken(e.target.value)}
                      className="font-mono text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold">Telegram Chat ID(s)</label>
                    <Input
                      type="text"
                      placeholder="e.g. 123456789"
                      value={chatId}
                      onChange={(e) => setChatId(e.target.value)}
                      className="font-mono text-xs"
                    />
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <Button type="submit" disabled={isSavingTelegram} size="sm" className="gap-1.5">
                    <Save className="h-3.5 w-3.5" />
                    {isSavingTelegram ? 'Saving...' : 'Save Telegram Config'}
                  </Button>

                  <Button type="button" onClick={handleTestTelegram} disabled={isTestingTelegram} variant="outline" size="sm" className="gap-1.5">
                    <Send className="h-3.5 w-3.5" />
                    {isTestingTelegram ? 'Sending...' : 'Send Test Telegram Alert'}
                  </Button>
                </div>
              </form>

              {telegramResult && (
                <div className={`flex items-center gap-2 p-2.5 rounded-md text-xs border ${
                  telegramResult.type === 'success' 
                    ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800' 
                    : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
                }`}>
                  {telegramResult.type === 'success' ? <CheckCircle className="h-4 w-4 shrink-0" /> : <XCircle className="h-4 w-4 shrink-0" />}
                  <span>{telegramResult.message}</span>
                </div>
              )}

              {telegramTestResult && (
                <div className={`flex items-center gap-2 p-2.5 rounded-md text-xs border ${
                  telegramTestResult.type === 'success' 
                    ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800' 
                    : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
                }`}>
                  {telegramTestResult.type === 'success' ? <CheckCircle className="h-4 w-4 shrink-0" /> : <XCircle className="h-4 w-4 shrink-0" />}
                  <span>{telegramTestResult.message}</span>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: Camera Configuration */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-base font-semibold">
                <Camera className="h-5 w-5 text-primary" /> Step 3: Add Primary Security Camera
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Add your initial camera stream. Smart VMS supports Laptop Webcams, HTTP/MJPEG streams, and RTSP IP Cameras.
              </p>

              <div className="space-y-3 bg-secondary/30 p-4 rounded-lg border">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold">Camera Name</label>
                    <Input
                      type="text"
                      value={cameraName}
                      onChange={(e) => setCameraName(e.target.value)}
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold">Camera Type</label>
                    <select
                      value={cameraType}
                      onChange={(e) => {
                        setCameraType(e.target.value);
                        if (e.target.value === 'Laptop Webcam') setStreamUrl('0');
                        else setStreamUrl('');
                      }}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="Laptop Webcam">Laptop / USB Webcam</option>
                      <option value="HTTP / MJPEG">HTTP / MJPEG Stream</option>
                      <option value="HTTPS Stream">HTTPS Stream</option>
                      <option value="RTSP Camera">RTSP IP Camera</option>
                    </select>
                  </div>
                </div>

                {cameraType !== 'Laptop Webcam' && (
                  <div className="space-y-1">
                    <label className="text-xs font-semibold">Stream URL / RTSP Address</label>
                    <Input
                      type="text"
                      placeholder="rtsp://admin:password@192.168.1.100:554/stream1"
                      value={streamUrl}
                      onChange={(e) => setStreamUrl(e.target.value)}
                      className="font-mono text-xs"
                    />
                  </div>
                )}

                <div className="flex items-center gap-2 pt-1">
                  <Button type="button" onClick={handleTestCamera} disabled={isTestingCamera} variant="outline" size="sm" className="gap-1.5">
                    <Video className="h-3.5 w-3.5" />
                    {isTestingCamera ? 'Testing...' : 'Test Camera Connection'}
                  </Button>

                  <Button type="button" onClick={handleSaveCamera} disabled={isSavingCamera || cameraSaved} size="sm" className="gap-1.5">
                    <CheckCircle className="h-3.5 w-3.5" />
                    {cameraSaved ? 'Camera Added!' : isSavingCamera ? 'Adding...' : 'Add Camera'}
                  </Button>
                </div>
              </div>

              {cameraTestResult && (
                <div className={`p-3 rounded-md text-xs border ${
                  cameraTestResult.type === 'success' 
                    ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800' 
                    : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
                }`}>
                  <div className="flex items-center gap-2">
                    {cameraTestResult.type === 'success' ? <CheckCircle className="h-4 w-4 shrink-0" /> : <XCircle className="h-4 w-4 shrink-0" />}
                    <span>{cameraTestResult.message}</span>
                  </div>
                  {cameraTestResult.type === 'blocked' && (
                    <Button 
                      type="button"
                      variant="outline" 
                      size="sm"
                      className="mt-2.5 text-xs w-full"
                      onClick={() => { window.location.href = 'ms-settings:privacy-webcam'; }}
                    >
                      Open Windows Settings
                    </Button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* STEP 4: Completion */}
          {step === 4 && (
            <div className="space-y-6 text-center py-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-green-500/10 text-green-500 flex items-center justify-center border border-green-500/30">
                <Sparkles className="h-8 w-8 animate-bounce" />
              </div>
              
              <div className="space-y-2">
                <h3 className="text-2xl font-bold tracking-tight text-foreground">
                  Smart VMS setup is complete.
                </h3>
                <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                  All system components, database connections, security parameters, and alert configurations have been saved securely.
                </p>
              </div>

              <div className="pt-2">
                <Button onClick={handleCompleteSetup} size="lg" className="px-8 gap-2 font-semibold">
                  <CheckCircle className="h-5 w-5" /> Launch Dashboard
                </Button>
              </div>
            </div>
          )}

        </div>

        {/* Footer Navigation Controls */}
        <div className="p-4 bg-muted/40 border-t border-border flex items-center justify-between">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1 || step === 4}
            className="gap-1.5"
          >
            <ArrowLeft className="h-4 w-4" /> Back
          </Button>

          {step < 4 && (
            <Button 
              size="sm"
              onClick={() => setStep((s) => Math.min(4, s + 1))}
              className="gap-1.5"
            >
              Next Step <ArrowRight className="h-4 w-4" />
            </Button>
          )}
        </div>

      </div>
    </div>
  );
}
