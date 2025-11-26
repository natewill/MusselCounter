const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const net = require('net');

const logFile = path.join(app.getPath('userData'), 'mussel-electron.log');
function log(message) {
  const line = `[${new Date().toISOString()}] ${message}`;
  console.log(line);
  try {
    fs.appendFileSync(logFile, `${line}\n`);
  } catch (err) {
    console.error('Failed to write log:', err);
  }
}

// Ensure only one instance
const singleInstanceLock = app.requestSingleInstanceLock();
if (!singleInstanceLock) {
  app.quit();
}

const HOST = '127.0.0.1';
const FRONTEND_PORT = Number(process.env.FRONTEND_PORT) || 3000;
const BACKEND_PORT = Number(process.env.BACKEND_PORT) || 8000;
const DEFAULT_PATH =
  process.env.PATH ||
  '/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin';

const baseDir = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..');
const backendDir = path.join(baseDir, 'backend');
const frontendDir = path.join(baseDir, 'frontend');

const bundledRuntimeDir = path.join(backendDir, 'python-runtime', process.platform === 'win32' ? 'Scripts' : 'bin');
const bundledPython = path.join(
  backendDir,
  'python-runtime',
  process.platform === 'win32' ? 'Scripts' : 'bin',
  process.platform === 'win32' ? 'python.exe' : 'python3'
);

// Prefer bundled runtime automatically when present
if (!process.env.PYTHON_PATH && fs.existsSync(bundledPython)) {
  process.env.PYTHON_PATH = bundledPython;
}

let backendProcess;
let frontendProcess;

function resolvePythonPath() {
  if (process.env.PYTHON_PATH) {
    return process.env.PYTHON_PATH;
  }

  const bundledRuntime = path.join(backendDir, 'python-runtime');
  const bundledPython = process.platform === 'win32'
    ? path.join(bundledRuntime, 'Scripts', 'python.exe')
    : path.join(bundledRuntime, 'bin', 'python3');

  if (fs.existsSync(bundledPython)) {
    return bundledPython;
  }

  const posixVenv = path.join(backendDir, 'venv', 'bin', 'python');
  const windowsVenv = path.join(backendDir, 'venv', 'Scripts', 'python.exe');

  if (fs.existsSync(posixVenv)) {
    return posixVenv;
  }
  if (fs.existsSync(windowsVenv)) {
    return windowsVenv;
  }

  const candidates = [
    process.platform === 'win32' ? 'python' : 'python3',
    '/usr/bin/python3',
    '/opt/homebrew/bin/python3',
    '/usr/local/bin/python3',
  ];

  for (const candidate of candidates) {
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return candidate;
    } catch (e) {
      continue;
    }
  }

  return process.platform === 'win32' ? 'python' : 'python3';
}

function startBackend() {
  const pythonCmd = resolvePythonPath();
  const args = ['-m', 'uvicorn', 'main:app', '--host', HOST, '--port', String(BACKEND_PORT)];

  log(`Starting backend with ${pythonCmd} ${args.join(' ')}`);
  const proc = spawn(pythonCmd, args, {
    cwd: backendDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      PATH: fs.existsSync(bundledRuntimeDir)
        ? `${bundledRuntimeDir}${path.delimiter}${DEFAULT_PATH}`
        : DEFAULT_PATH,
    },
  });

  proc.stdout.on('data', (data) => log(`[backend] ${data.toString().trim()}`));
  proc.stderr.on('data', (data) => log(`[backend] ${data.toString().trim()}`));

  proc.on('exit', (code) => {
    log(`[backend] exited with code ${code ?? 'unknown'}`);
  });

  proc.on('error', (err) => {
    log(`[backend] failed to start: ${err.message}`);
  });

  return proc;
}

function resolveNextBinary() {
  const nextBin = path.join(frontendDir, 'node_modules', 'next', 'dist', 'bin', 'next');
  return fs.existsSync(nextBin) ? nextBin : null;
}

function startFrontend() {
  const hasBuild = fs.existsSync(path.join(frontendDir, '.next'));
  const useDevServer = process.env.NEXT_DEV === 'true' || !hasBuild;
  const script = useDevServer ? 'dev' : 'start';

  const nextBin = resolveNextBinary();
  if (!nextBin) {
    dialog.showErrorBox(
      'Missing Next.js binary',
      'Could not find Next.js in frontend/node_modules. Please run "npm install" in the frontend directory before packaging.'
    );
    app.quit();
    return { proc: null, script };
  }

  if (!useDevServer && !hasBuild) {
    dialog.showErrorBox(
      'Frontend build missing',
      'No .next build found. Run "npm run build" in the frontend directory before packaging, or set NEXT_DEV=true to run the dev server.'
    );
    log('Frontend build missing (.next not found)');
    app.quit();
    return { proc: null, script };
  }

  const args = [
    nextBin,
    script,
    '--hostname',
    HOST,
    '--port',
    String(FRONTEND_PORT),
  ];

  log(`Starting frontend with ${process.execPath} ${args.join(' ')}`);
  const proc = spawn(process.execPath, args, {
    cwd: frontendDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      PATH: DEFAULT_PATH,
      NODE_ENV: useDevServer ? 'development' : 'production',
      ELECTRON_RUN_AS_NODE: '1',
    },
  });

  proc.stdout.on('data', (data) => log(`[frontend] ${data.toString().trim()}`));
  proc.stderr.on('data', (data) => log(`[frontend] ${data.toString().trim()}`));

  proc.on('exit', (code) => {
    log(`[frontend (${script})] exited with code ${code ?? 'unknown'}`);
    if (code && code !== 0) {
      dialog.showErrorBox(
        'Frontend exited',
        `Next.js ${script} exited with code ${code}. See log at ${logFile}`
      );
    }
  });

  proc.on('error', (err) => {
    log(`[frontend] failed to start: ${err.message}`);
    dialog.showErrorBox('Frontend start error', err.message);
  });

  return { proc, script };
}

function waitForServer(port, label) {
  const timeoutMs = 60000;
  const start = Date.now();

  return new Promise((resolve, reject) => {
    const attempt = () => {
      log(`[waitForServer] checking ${label} on port ${port}`);
      const socket = net.createConnection({ port, host: HOST }, () => {
        socket.end();
        log(`[waitForServer] ${label} is up on port ${port}`);
        resolve(true);
      });

      socket.on('error', () => {
        socket.destroy();
        if (Date.now() - start > timeoutMs) {
          log(`[waitForServer] ${label} timed out on port ${port}`);
          reject(new Error(`${label} did not start on port ${port}. Check logs for details.`));
        } else {
          setTimeout(attempt, 500);
        }
      });
    };

    attempt();
  });
}

async function createWindow() {
  try {
    await waitForServer(BACKEND_PORT, 'Backend');
  } catch (err) {
    dialog.showErrorBox('Startup error', err.message);
    log(`Startup error: ${err.message}`);
    app.quit();
    return;
  }

  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      contextIsolation: true,
    },
  });

  try {
    await waitForServer(FRONTEND_PORT, 'Frontend');
  } catch (err) {
    log(`Frontend did not start: ${err.message}`);
    dialog.showErrorBox(
      'Frontend failed to start',
      `${err.message}\n\nSee log at ${logFile}`
    );
    app.quit();
    return;
  }

  try {
    await win.loadURL(`http://${HOST}:${FRONTEND_PORT}`);
  } catch (err) {
    log(`Failed to load frontend: ${err.message}`);
    dialog.showErrorBox('Failed to load UI', `${err.message}\n\nSee log at ${logFile}`);
    app.quit();
  }
}

function cleanUp() {
  if (frontendProcess && !frontendProcess.killed) {
    frontendProcess.kill();
  }

  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
}

app.whenReady().then(() => {
  backendProcess = startBackend();
  ({ proc: frontendProcess } = startFrontend());
  // Load window immediately; Next.js will come up shortly after on the same port
  createWindow();
});

app.on('second-instance', () => {
  const [win] = BrowserWindow.getAllWindows();
  if (win) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', cleanUp);
process.on('SIGINT', () => {
  cleanUp();
  app.quit();
});
process.on('SIGTERM', () => {
  cleanUp();
  app.quit();
});
