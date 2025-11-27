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

const bundledRuntimeDir = path.join(
  backendDir,
  'python-runtime',
  process.platform === 'win32' ? 'Scripts' : 'bin'
);
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

// Prefer a real Node.js binary; do NOT fall back to Electron
function resolveNodePath() {
  const candidates = [
    process.env.NODE_BINARY,
    process.env.NEXT_NODE_BINARY,
    path.join(frontendDir, 'node_modules', '.bin', 'node'),
    '/opt/homebrew/bin/node',
    '/usr/local/bin/node',
    '/usr/bin/node',
    'node',
  ].filter(Boolean);

  for (const candidate of candidates) {
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      log(`[resolveNodePath] Using Node at ${candidate}`);
      return candidate;
    } catch (err) {
      continue;
    }
  }

  log('[resolveNodePath] No Node.js binary found in candidates');
  return null;
}

function resolvePythonPath() {
  if (process.env.PYTHON_PATH) {
    log(`[resolvePythonPath] Using PYTHON_PATH=${process.env.PYTHON_PATH}`);
    return process.env.PYTHON_PATH;
  }

  const bundledRuntime = path.join(backendDir, 'python-runtime');
  const bundledPython = process.platform === 'win32'
    ? path.join(bundledRuntime, 'Scripts', 'python.exe')
    : path.join(bundledRuntime, 'bin', 'python3');

  if (fs.existsSync(bundledPython)) {
    log(`[resolvePythonPath] Using bundled runtime at ${bundledPython}`);
    return bundledPython;
  }

  const posixVenv = path.join(backendDir, 'venv', 'bin', 'python');
  const windowsVenv = path.join(backendDir, 'venv', 'Scripts', 'python.exe');

  if (fs.existsSync(posixVenv)) {
    log(`[resolvePythonPath] Using backend venv at ${posixVenv}`);
    return posixVenv;
  }
  if (fs.existsSync(windowsVenv)) {
    log(`[resolvePythonPath] Using backend venv at ${windowsVenv}`);
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
      log(`[resolvePythonPath] Using system python at ${candidate}`);
      return candidate;
    } catch (e) {
      continue;
    }
  }

  log('[resolvePythonPath] Falling back to platform default python');
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
  log(`[frontend] hasBuild=${hasBuild} useDevServer=${useDevServer} script=${script}`);

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

  const nodeCmd = resolveNodePath();
  if (!nodeCmd) {
    log('[frontend] No Node.js runtime found.');
    dialog.showErrorBox(
      'Node.js not found',
      'Could not find a Node.js runtime to start the frontend. Install Node.js, or set NODE_BINARY/NEXT_NODE_BINARY to the Node path, or bundle Node with the app.'
    );
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

  log(`Starting frontend with ${nodeCmd} ${args.join(' ')}`);

  const env = {
    ...process.env,
    PATH: DEFAULT_PATH,
    NODE_ENV: useDevServer ? 'development' : 'production',
  };
  delete env.ELECTRON_RUN_AS_NODE;

  const proc = spawn(nodeCmd, args, {
    cwd: frontendDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    env,
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
  log(`[waitForServer] begin wait for ${label} on port ${port}`);

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
  log('[createWindow] starting window creation');
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
    log(`[createWindow] loading URL http://${HOST}:${FRONTEND_PORT}`);
    await win.loadURL(`http://${HOST}:${FRONTEND_PORT}`);
  } catch (err) {
    log(`Failed to load frontend: ${err.message}`);
    dialog.showErrorBox('Failed to load UI', `${err.message}\n\nSee log at ${logFile}`);
    app.quit();
  }
}

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

app.whenReady().then(() => {
  log('[lifecycle] app ready');
  backendProcess = startBackend();
  ({ proc: frontendProcess } = startFrontend());
  // Load window immediately; Next.js will come up shortly after on the same port
  createWindow();
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
    createWindow();
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
