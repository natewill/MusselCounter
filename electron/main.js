const { app, BrowserWindow, dialog } = require('electron');

const { HOST, FRONTEND_PORT, BACKEND_PORT } = require('./config');
const { createLogger } = require('./logger');
const { startBackend } = require('./backend');
const { startFrontend } = require('./frontend');
const { ensurePortsAvailable, createWindow } = require('./lifecycle');

const { log, logFile } = createLogger(app);

const singleInstanceLock = app.requestSingleInstanceLock();
if (!singleInstanceLock) {
  app.quit();
}

let backendProcess = null;
let frontendProcess = null;

function cleanUp() {
  if (frontendProcess && !frontendProcess.killed) {
    log('[cleanup] killing frontend process');
    frontendProcess.kill();
  }

  if (backendProcess && !backendProcess.killed) {
    log('[cleanup] killing backend process');
    backendProcess.kill();
  }
}

app.whenReady().then(async () => {
  log('[lifecycle] app ready');
  log(`[lifecycle] Platform: ${process.platform}`);
  log(`[lifecycle] Electron version: ${process.versions.electron}`);
  log(`[lifecycle] Node version: ${process.versions.node}`);
  log(`[lifecycle] App path: ${app.getAppPath()}`);
  log(`[lifecycle] User data path: ${app.getPath('userData')}`);
  log(`[lifecycle] Log file: ${logFile}`);

  try {
    await ensurePortsAvailable({
      host: HOST,
      ports: [BACKEND_PORT, FRONTEND_PORT],
      log,
    });
  } catch (err) {
    dialog.showErrorBox(
      'Ports In Use',
      `${err.message}\n\nClose those processes and start the app again.`
    );
    app.quit();
    return;
  }

  log('[lifecycle] starting backend...');
  backendProcess = startBackend({
    app,
    host: HOST,
    backendPort: BACKEND_PORT,
    log,
  });

  if (!backendProcess) {
    app.quit();
    return;
  }

  log('[lifecycle] starting frontend...');
  frontendProcess = startFrontend({
    app,
    host: HOST,
    frontendPort: FRONTEND_PORT,
    log,
  });

  if (!frontendProcess) {
    cleanUp();
    app.quit();
    return;
  }

  try {
    await createWindow({
      host: HOST,
      frontendPort: FRONTEND_PORT,
      backendPort: BACKEND_PORT,
      log,
      logFile,
    });
  } catch (err) {
    log(`[lifecycle] startup failed: ${err.message}`);
    cleanUp();
    app.quit();
  }
});

app.on('second-instance', () => {
  log('[lifecycle] second-instance detected');
  const [win] = BrowserWindow.getAllWindows();
  if (win) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
});

app.on('window-all-closed', () => {
  log('[lifecycle] window-all-closed');
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  log('[lifecycle] activate');
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow({
      host: HOST,
      frontendPort: FRONTEND_PORT,
      backendPort: BACKEND_PORT,
      log,
      logFile,
    }).catch((err) => {
      log(`[lifecycle] activate createWindow failed: ${err.message}`);
    });
  }
});

app.on('before-quit', cleanUp);
process.on('SIGINT', () => {
  log('[signal] SIGINT received');
  cleanUp();
  app.quit();
});
process.on('SIGTERM', () => {
  log('[signal] SIGTERM received');
  cleanUp();
  app.quit();
});
