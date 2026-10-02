import React, { useState, useEffect } from 'react';
import { Database, CheckCircle, AlertTriangle, RefreshCw, XCircle, Key } from 'lucide-react';
import { getDbStatus, saveDbConfig } from '../services/systemService';
import { Button } from './ui/button';

export default function DbStatusBadge() {
  const [dbStatus, setDbStatus] = useState({ status: 'connecting', configured: true, message: '' });
  const [isOpen, setIsOpen] = useState(false);
  const [mongoUri, setMongoUri] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [configResult, setConfigResult] = useState(null);

  const fetchStatus = async () => {
    try {
      const data = await getDbStatus();
      setDbStatus(data);
    } catch {
      setDbStatus({ status: 'disconnected', configured: false, message: 'Backend unreachable' });
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    if (!mongoUri.trim()) return;

    setIsSaving(true);
    setConfigResult(null);

    try {
      const res = await saveDbConfig(mongoUri);
      if (res.success) {
        setConfigResult({ type: 'success', message: res.message || 'MongoDB Atlas connected successfully!' });
        setMongoUri('');
        fetchStatus();
        setTimeout(() => setIsOpen(false), 2000);
      } else {
        setConfigResult({ type: 'error', message: res.message || 'Failed to connect to MongoDB Atlas.' });
      }
    } catch (err) {
      const errDetail = err.response?.data?.detail || 'Unable to connect to MongoDB Atlas. Check your URI & internet.';
      setConfigResult({ type: 'error', message: errDetail });
    } finally {
      setIsSaving(false);
    }
  };

  const renderBadge = () => {
    switch (dbStatus.status) {
      case 'connected':
        return (
          <button
            onClick={() => setIsOpen(true)}
            className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-green-500/10 text-green-500 border border-green-500/20 hover:bg-green-500/20 transition-all cursor-pointer"
            title="MongoDB Atlas Connected. Click to configure."
          >
            <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            <Database className="h-3.5 w-3.5" />
            <span>Atlas Connected</span>
          </button>
        );
      case 'reconnecting':
        return (
          <button
            onClick={() => setIsOpen(true)}
            className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20 hover:bg-amber-500/20 transition-all cursor-pointer"
            title="MongoDB Atlas Reconnecting. Click to configure."
          >
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            <span>Atlas Reconnecting...</span>
          </button>
        );
      case 'unconfigured':
        return (
          <button
            onClick={() => setIsOpen(true)}
            className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/20 hover:bg-blue-500/20 transition-all cursor-pointer"
            title="MongoDB Atlas Unconfigured. Click to setup."
          >
            <Key className="h-3.5 w-3.5" />
            <span>Configure MongoDB</span>
          </button>
        );
      default:
        return (
          <button
            onClick={() => setIsOpen(true)}
            className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-500 border border-red-500/20 hover:bg-red-500/20 transition-all cursor-pointer"
            title="MongoDB Atlas Offline. Click to reconfigure."
          >
            <span className="h-2 w-2 rounded-full bg-red-500" />
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>Atlas Offline</span>
          </button>
        );
    }
  };

  return (
    <>
      {renderBadge()}

      {/* MongoDB Configuration Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-2xl p-6 space-y-4 relative">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2 text-lg font-bold">
                <Database className="h-5 w-5 text-primary" />
                MongoDB Atlas Setup
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-bold px-2 py-1 rounded-md"
              >
                ✕
              </button>
            </div>

            <div className="text-xs text-muted-foreground space-y-1">
              <p>Configure your cloud MongoDB Atlas connection for Smart VMS.</p>
              <p className="text-[11px] opacity-85">
                Credentials are validated via backend 5s test and encrypted using Windows DPAPI before local storage.
              </p>
            </div>

            <form onSubmit={handleSaveConfig} className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-foreground">MongoDB Atlas URI</label>
                <input
                  type="password"
                  placeholder="mongodb+srv://<user>:<password>@cluster.mongodb.net/smart_vms"
                  value={mongoUri}
                  onChange={(e) => setMongoUri(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md bg-background border border-border text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
                  required
                />
              </div>

              {configResult && (
                <div
                  className={`flex items-start gap-2 p-3 rounded-md text-xs border ${
                    configResult.type === 'success'
                      ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800'
                      : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
                  }`}
                >
                  {configResult.type === 'success' ? (
                    <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  )}
                  <span>{configResult.message}</span>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" type="button" onClick={() => setIsOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSaving || !mongoUri.trim()}>
                  {isSaving ? 'Validating...' : 'Connect & Save'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
