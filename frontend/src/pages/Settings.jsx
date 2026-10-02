import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Server, Database, Code, CheckCircle, Send, Bell, XCircle, Save, ShieldCheck } from 'lucide-react';
import { useTheme } from '../context/ThemeProvider';
import api from '../services/api';

import { getDbStatus } from '../services/systemService';

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const [telegramStatus, setTelegramStatus] = useState({ enabled: false, configured: false, hasBotToken: false, maskedToken: '', chatId: '' });
  const [dbStatus, setDbStatus] = useState({ status: 'connecting', configured: true, message: '' });
  
  // Telegram Config Form States
  const [enabled, setEnabled] = useState(false);
  const [botToken, setBotToken] = useState('');
  const [chatId, setChatId] = useState('');
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [saveResult, setSaveResult] = useState(null);

  const [isSendingTest, setIsSendingTest] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    fetchTelegramStatus();
    fetchDbStatus();
  }, []);

  const fetchDbStatus = async () => {
    try {
      const data = await getDbStatus();
      setDbStatus(data);
    } catch {
      setDbStatus({ status: 'disconnected', configured: false, message: 'Backend unreachable' });
    }
  };

  const fetchTelegramStatus = async () => {
    try {
      const res = await api.get('/notifications/telegram/status');
      setTelegramStatus(res.data);
      setEnabled(res.data.enabled ?? false);
      if (res.data.chatId) {
        setChatId(res.data.chatId);
      }
    } catch {
      console.error("Failed to fetch Telegram status");
    }
  };

  const handleSaveTelegramConfig = async (e) => {
    if (e) e.preventDefault();
    setIsSavingConfig(true);
    setSaveResult(null);
    try {
      const payload = {
        enabled,
        botToken: botToken.trim() ? botToken.trim() : undefined,
        chatId: chatId.trim(),
      };
      const res = await api.post('/notifications/telegram/config', payload);
      setSaveResult({ type: 'success', message: res.data.message || 'Telegram configuration saved successfully.' });
      setBotToken(''); // Clear plain text token input after successful save
      await fetchTelegramStatus();
    } catch (err) {
      setSaveResult({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to save Telegram configuration.',
      });
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleSendTestAlert = async () => {
    setIsSendingTest(true);
    setTestResult(null);
    try {
      const res = await api.post('/notifications/telegram/test');
      if (res.data.success) {
        setTestResult({ type: 'success', message: res.data.message || 'Smart VMS Telegram test alert — connection successful.' });
      } else {
        setTestResult({ type: 'error', message: res.data.message || 'Failed to send Telegram notification.' });
      }
    } catch (err) {
      setTestResult({ type: 'error', message: err.response?.data?.message || 'Failed to send Telegram notification. Check credentials.' });
    } finally {
      setIsSendingTest(false);
    }
  };

  const isProduction = window.location.protocol === 'file:' || process.env.NODE_ENV === 'production';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">System Settings</h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="h-5 w-5 text-primary" /> Application Info
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">Version</span>
              <span className="font-medium">1.0.0</span>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">Environment</span>
              <span className="font-medium">{isProduction ? 'Production' : 'Development'}</span>
            </div>

            <div className="flex justify-between pb-2 items-center">
              <span className="text-muted-foreground">Theme</span>
              <div className="flex gap-2">
                <Button 
                  variant={theme === 'light' ? 'default' : 'outline'} 
                  size="sm" 
                  onClick={() => setTheme('light')}
                >
                  Light
                </Button>
                <Button 
                  variant={theme === 'dark' ? 'default' : 'outline'} 
                  size="sm" 
                  onClick={() => setTheme('dark')}
                >
                  Dark
                </Button>
                <Button 
                  variant={theme === 'system' ? 'default' : 'outline'} 
                  size="sm" 
                  onClick={() => setTheme('system')}
                >
                  System
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-primary" /> Database Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">Provider</span>
              <span className="font-medium">MongoDB Atlas</span>
            </div>
            <div className="flex justify-between border-b pb-2 items-center">
              <span className="text-muted-foreground">Connection State</span>
              {dbStatus.status === 'connected' && (
                <span className="font-medium flex items-center gap-2 text-green-500 bg-green-500/10 px-2.5 py-0.5 rounded-full text-xs">
                  <CheckCircle className="h-3.5 w-3.5" /> Connected
                </span>
              )}
              {dbStatus.status === 'reconnecting' && (
                <span className="font-medium flex items-center gap-2 text-amber-500 bg-amber-500/10 px-2.5 py-0.5 rounded-full text-xs">
                  <span className="h-2 w-2 rounded-full bg-amber-500 animate-ping" /> Reconnecting
                </span>
              )}
              {dbStatus.status === 'unconfigured' && (
                <span className="font-medium flex items-center gap-2 text-blue-500 bg-blue-500/10 px-2.5 py-0.5 rounded-full text-xs">
                  <XCircle className="h-3.5 w-3.5" /> Unconfigured
                </span>
              )}
              {dbStatus.status === 'disconnected' && (
                <span className="font-medium flex items-center gap-2 text-red-500 bg-red-500/10 px-2.5 py-0.5 rounded-full text-xs">
                  <XCircle className="h-3.5 w-3.5" /> Offline
                </span>
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              {dbStatus.message || 'Connecting to backend...'}
            </div>
          </CardContent>
        </Card>

        {/* Telegram Alerts Section */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bell className="h-5 w-5 text-primary" /> Telegram Intrusion Alerts
              </div>
              <div className="flex items-center gap-2">
                {telegramStatus.configured ? (
                  <span className="flex items-center gap-1 text-green-500 bg-green-500/10 px-2.5 py-0.5 rounded-full text-xs font-medium">
                    <CheckCircle className="h-3.5 w-3.5" /> Configured
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-amber-500 bg-amber-500/10 px-2.5 py-0.5 rounded-full text-xs font-medium">
                    <XCircle className="h-3.5 w-3.5" /> Unconfigured
                  </span>
                )}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center justify-between p-4 rounded-lg bg-secondary/50 border">
              <div>
                <p className="font-medium text-sm">Enable Telegram Intrusion Alerts</p>
                <p className="text-xs text-muted-foreground">Send real-time instant alerts, snapshot images, and video clips upon zone intrusions.</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={enabled} 
                  onChange={(e) => setEnabled(e.target.checked)}
                  className="sr-only peer" 
                />
                <div className="w-11 h-6 bg-muted peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>

            <form onSubmit={handleSaveTelegramConfig} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground flex items-center justify-between">
                    <span>Telegram Bot Token</span>
                    {telegramStatus.hasBotToken && (
                      <span className="text-[10px] text-green-600 dark:text-green-400 flex items-center gap-1 font-normal">
                        <ShieldCheck className="h-3 w-3" /> Encrypted & Saved
                      </span>
                    )}
                  </label>
                  <Input
                    type="password"
                    value={botToken}
                    onChange={(e) => setBotToken(e.target.value)}
                    placeholder={telegramStatus.hasBotToken ? (telegramStatus.maskedToken || '••••••••••••••••') : 'Enter Bot Token from @BotFather'}
                    className="font-mono text-xs"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Obtained from Telegram @BotFather (e.g. 123456789:ABCdef...). Leave blank to retain saved token.
                  </p>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Telegram Chat ID(s)</label>
                  <Input
                    type="text"
                    value={chatId}
                    onChange={(e) => setChatId(e.target.value)}
                    placeholder="e.g. 123456789 or comma-separated IDs"
                    className="font-mono text-xs"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Your Telegram Chat ID or Channel ID. Use comma separation for multiple recipients.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <Button 
                  type="submit" 
                  disabled={isSavingConfig} 
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  {isSavingConfig ? 'Saving...' : 'Save Configuration'}
                </Button>

                <Button 
                  type="button" 
                  onClick={handleSendTestAlert} 
                  disabled={isSendingTest || !telegramStatus.configured} 
                  variant="outline" 
                  className="gap-2"
                >
                  <Send className="h-4 w-4" />
                  {isSendingTest ? 'Sending...' : 'Send Test Telegram Alert'}
                </Button>
              </div>
            </form>

            {saveResult && (
              <div className={`flex items-center gap-2 p-3 rounded-md text-xs border ${
                saveResult.type === 'success' 
                  ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800' 
                  : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
              }`}>
                {saveResult.type === 'success' ? <CheckCircle className="h-4 w-4 shrink-0" /> : <XCircle className="h-4 w-4 shrink-0" />}
                <span>{saveResult.message}</span>
              </div>
            )}

            {testResult && (
              <div className={`flex items-center gap-2 p-3 rounded-md text-xs border ${
                testResult.type === 'success' 
                  ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800' 
                  : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
              }`}>
                {testResult.type === 'success' ? <CheckCircle className="h-4 w-4 shrink-0" /> : <XCircle className="h-4 w-4 shrink-0" />}
                <span>{testResult.message}</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5 text-primary" /> Backend API Status
            </CardTitle>
          </CardHeader>
          <CardContent>
             <div className="flex items-center justify-between p-4 rounded-lg bg-secondary/50 border">
              <div>
                <p className="font-medium">FastAPI Server</p>
                <p className="text-sm text-muted-foreground">http://localhost:8000</p>
              </div>
              <div className="flex items-center gap-2 text-green-500 bg-green-500/10 px-3 py-1 rounded-full text-sm font-medium">
                <CheckCircle className="h-4 w-4" />
                Online
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

