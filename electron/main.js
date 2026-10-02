const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const http = require('http');
const { spawn, execSync } = require('child_process');

let splashWindow = null;
let mainWindow = null;
let backendProcess = null;
const BACKEND_PORT = process.env.BACKEND_PORT || 8000;
const BACKEND_HOST = '127.0.0.1';
const HEALTH_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/health`;

// 0. Create Dedicated Startup Splash Window
function createSplashWindow() {
  const iconPath = path.join(__dirname, 'icon.png');
  splashWindow = new BrowserWindow({
    width: 520,
    height: 340,
    frame: false,
    transparent: false,
    backgroundColor: '#090d16',
    resizable: false,
    center: true,
    alwaysOnTop: true,
    show: false,
    skipTaskbar: false,
    icon: iconPath,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  splashWindow.loadFile(path.join(__dirname, 'splash.html'));

  splashWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.show();
    }
  });

  splashWindow.on('closed', () => {
    splashWindow = null;
  });
}

// 1. Resolve Packaged backend.exe Path
function getBackendExecutablePath() {
  const isPackaged = app.isPackaged;
  if (isPackaged) {
    // Production electron-builder structure
    return path.join(process.resourcesPath, 'backend', 'backend.exe');
  }

  // Development / Integration Stage
  const rootDistPath = path.join(__dirname, '..', 'dist', 'backend', 'backend.exe');
  const backendDistPath = path.join(__dirname, '..', 'backend', 'dist', 'backend', 'backend.exe');

  if (require('fs').existsSync(rootDistPath)) {
    return rootDistPath;
  }
  return backendDistPath;
}

function killExistingBackend() {
  try {
    if (process.platform === 'win32') {
      execSync('taskkill /F /IM backend.exe /T', { stdio: 'ignore' });
    }
  } catch (e) {
    // Process wasn't running, ignore
  }
}

const recentBackendLogs = [];
let backendExitError = null;

function appendBackendLog(msg) {
  recentBackendLogs.push(msg);
  if (recentBackendLogs.length > 30) {
    recentBackendLogs.shift();
  }
}

// 2. Start Packaged backend.exe Child Process
function startBackendProcess() {
  killExistingBackend();
  backendExitError = null;
  recentBackendLogs.length = 0;

  const backendExe = getBackendExecutablePath();

  console.log('[ELECTRON MAIN] Resolving backend executable path:', backendExe);

  if (!require('fs').existsSync(backendExe)) {
    const errorMsg = `Backend executable not found at:\n${backendExe}\n\nPlease run PyInstaller build first.`;
    console.error('[ELECTRON ERROR]', errorMsg);
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    dialog.showErrorBox('Smart VMS Startup Error', errorMsg);
    app.quit();
    return false;
  }

  const cwd = path.dirname(backendExe);
  console.log('[ELECTRON MAIN] Spawning backend child process with CWD:', cwd);

  try {
    const logDir = path.join(app.getPath('userData'), 'logs');
    if (!require('fs').existsSync(logDir)) {
      require('fs').mkdirSync(logDir, { recursive: true });
    }
    const logFile = path.join(logDir, 'backend_process.log');
    const logStream = require('fs').createWriteStream(logFile, { flags: 'a' });

    backendProcess = spawn(
      backendExe,
      ['--host', BACKEND_HOST, '--port', String(BACKEND_PORT)],
      {
        cwd: cwd,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe']
      }
    );

    backendProcess.stdout.on('data', (data) => {
      const text = data.toString().trim();
      const msg = `[BACKEND STDOUT] ${text}`;
      console.log(msg);
      appendBackendLog(msg);
      try { logStream.write(msg + '\n'); } catch (e) {}
    });

    backendProcess.stderr.on('data', (data) => {
      const text = data.toString().trim();
      const msg = `[BACKEND STDERR] ${text}`;
      console.error(msg);
      appendBackendLog(msg);
      try { logStream.write(msg + '\n'); } catch (e) {}
    });

    backendProcess.on('exit', (code, signal) => {
      console.warn(`[ELECTRON MAIN] Backend process exited with code ${code}, signal ${signal}`);
      if (code !== 0 && code !== null) {
        backendExitError = `Backend process exited prematurely with code ${code}.`;
      }
    });

    backendProcess.on('error', (err) => {
      console.error('[ELECTRON MAIN] Failed to spawn backend process:', err);
      backendExitError = `Failed to spawn backend process: ${err.message}`;
    });

    return true;
  } catch (err) {
    console.error('[ELECTRON MAIN] Exception starting backend process:', err);
    backendExitError = `Failed to start backend process: ${err.message}`;
    return false;
  }
}

// 3. Poll Backend Health Check Endpoint
function waitForBackend(timeoutMs = 45000) {
  const startTime = Date.now();

  return new Promise((resolve, reject) => {
    const interval = setInterval(() => {
      if (backendExitError) {
        clearInterval(interval);
        const logSnippet = recentBackendLogs.join('\n');
        reject(new Error(`${backendExitError}\n\nRecent Backend Logs:\n${logSnippet || '(none)'}`));
        return;
      }

      if (Date.now() - startTime > timeoutMs) {
        clearInterval(interval);
        const logSnippet = recentBackendLogs.join('\n');
        reject(new Error(`Backend health check timed out after ${timeoutMs / 1000}s\n\nRecent Backend Logs:\n${logSnippet || '(none)'}`));
        return;
      }

      http
        .get(HEALTH_URL, (res) => {
          if (res.statusCode === 200) {
            clearInterval(interval);
            console.log('[ELECTRON MAIN] Backend health check PASSED (HTTP 200 OK)');
            resolve(true);
          }
        })
        .on('error', () => {
          // Keep retrying while backend boots up
        });
    }, 500);
  });
}

// 4. Create Desktop BrowserWindow
function createMainWindow() {
  const iconPath = path.join(__dirname, 'icon.png');
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    title: 'Smart VMS',
    icon: iconPath,
    resizable: true,
    show: false, // Don't show until ready-to-show
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.once('ready-to-show', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.show();
    }
    // Cleanly close splash window after main window is ready
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
  });

  const isDevMode = process.env.NODE_ENV === 'development';
  const devServerUrl = 'http://localhost:5173';
  const distIndexPath = path.join(__dirname, '..', 'frontend', 'dist', 'index.html');

  if (isDevMode) {
    console.log('[ELECTRON MAIN] Loading Vite development server:', devServerUrl);
    mainWindow.loadURL(devServerUrl);
  } else if (require('fs').existsSync(distIndexPath)) {
    console.log('[ELECTRON MAIN] Loading React production bundle:', distIndexPath);
    mainWindow.loadFile(distIndexPath);
  } else {
    console.error('[ELECTRON ERROR] React production dist/index.html not found!');
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    dialog.showErrorBox(
      'Smart VMS Frontend Error',
      `React production build not found at:\n${distIndexPath}\n\nPlease run 'npm run build' in the frontend directory.`
    );
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 5. Clean Backend Process Termination
function stopBackendProcess() {
  if (backendProcess && !backendProcess.killed) {
    console.log('[ELECTRON MAIN] Terminating backend process PID:', backendProcess.pid);
    try {
      if (process.platform === 'win32') {
        execSync(`taskkill /pid ${backendProcess.pid} /T /F`, { stdio: 'ignore' });
      } else {
        backendProcess.kill('SIGTERM');
      }
    } catch (e) {
      console.error('[ELECTRON MAIN] Error terminating backend process:', e);
    }
    backendProcess = null;
  }
}

// 6. Electron Application Lifecycle Hooks
app.whenReady().then(async () => {
  console.log('==================================================');
  console.log('SMART VMS — ELECTRON DESKTOP INTEGRATION STARTUP');
  console.log('==================================================');

  // 1. Show Splash Screen immediately
  createSplashWindow();

  // 2. Start Backend process in background simultaneously
  const spawned = startBackendProcess();
  if (!spawned) return;

  try {
    console.log('[ELECTRON MAIN] Waiting for backend readiness and minimum splash screen duration...');
    const backendPromise = waitForBackend(45000);
    const minSplashPromise = new Promise((resolve) => setTimeout(resolve, 3000));

    // Wait for backend readiness AND ~3-second splash screen duration
    await Promise.all([backendPromise, minSplashPromise]);

    // 3. Create Main Application Window
    createMainWindow();
  } catch (err) {
    console.error('[ELECTRON MAIN] Backend failed to start:', err.message);
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    stopBackendProcess();
    dialog.showErrorBox(
      'Smart VMS Startup Error',
      `Failed to initialize Smart VMS Backend server:\n${err.message}`
    );
    app.quit();
  }
});

app.on('window-all-closed', () => {
  console.log('[ELECTRON MAIN] All windows closed. Exiting application.');
  stopBackendProcess();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackendProcess();
});

app.on('will-quit', () => {
  stopBackendProcess();
});

