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
  log(`[resolvePythonPath] Starting Python resolution`);
  log(`[resolvePythonPath] PYTHON_PATH env var: ${process.env.PYTHON_PATH || 'not set'}`);

  if (process.env.PYTHON_PATH) {
    log(`[resolvePythonPath] Using PYTHON_PATH=${process.env.PYTHON_PATH}`);
    return process.env.PYTHON_PATH;
  }

  const bundledRuntime = path.join(backendDir, 'python-runtime');
  const bundledPython = process.platform === 'win32'
    ? path.join(bundledRuntime, 'Scripts', 'python.exe')
    : path.join(bundledRuntime, 'bin', 'python3');

  log(`[resolvePythonPath] Checking bundled runtime: ${bundledPython}`);
  if (fs.existsSync(bundledPython)) {
    log(`[resolvePythonPath] Using bundled runtime at ${bundledPython}`);
    return bundledPython;
  } else {
    log(`[resolvePythonPath] Bundled runtime not found`);
  }

  const posixVenv = path.join(backendDir, 'venv', 'bin', 'python');
  const windowsVenv = path.join(backendDir, 'venv', 'Scripts', 'python.exe');

  log(`[resolvePythonPath] Checking venv: ${posixVenv}`);
  if (fs.existsSync(posixVenv)) {
    log(`[resolvePythonPath] Using backend venv at ${posixVenv}`);
    return posixVenv;
  }

  log(`[resolvePythonPath] Checking venv: ${windowsVenv}`);
  if (fs.existsSync(windowsVenv)) {
    log(`[resolvePythonPath] Using backend venv at ${windowsVenv}`);
    return windowsVenv;
  }

  log(`[resolvePythonPath] No venv found`);

  const candidates = [
    process.platform === 'win32' ? 'python' : 'python3',
    '/usr/bin/python3',
    '/opt/homebrew/bin/python3',
    '/usr/local/bin/python3',
  ];

  log(`[resolvePythonPath] Checking system Python candidates: ${candidates.join(', ')}`);
  for (const candidate of candidates) {
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      log(`[resolvePythonPath] Using system python at ${candidate}`);
      return candidate;
    } catch (e) {
      log(`[resolvePythonPath] Candidate ${candidate} not accessible: ${e.message}`);
    }
  }

  log('[resolvePythonPath] Falling back to platform default python');
  return process.platform === 'win32' ? 'python' : 'python3';
}

function killProcessOnPort(port) {
  return new Promise((resolve) => {
    const platform = process.platform;
    let command;
    let args;

    if (platform === 'win32') {
      // Windows: find PID using netstat, then kill with taskkill
      command = 'netstat';
      args = ['-ano'];
    } else {
      // macOS/Linux: use lsof to find and kill
      command = 'lsof';
      args = ['-ti', `:${port}`];
    }

    const proc = spawn(command, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: platform === 'win32', // Use shell on Windows for better compatibility
    });

    let output = '';
    proc.stdout.on('data', (data) => {
      output += data.toString();
    });

    proc.on('close', (code) => {
      if (platform === 'win32') {
        // Parse netstat output to find PID
        // netstat -ano output format: PROTO  LOCAL_ADDRESS  FOREIGN_ADDRESS  STATE  PID
        const lines = output.split('\n');
        const pids = new Set();
        
        for (const line of lines) {
          // Match lines with LISTENING state and our port
          if (line.includes('LISTENING') && line.includes(`:${port}`)) {
            // Extract PID (last column)
            const parts = line.trim().split(/\s+/);
            const pid = parts[parts.length - 1];
            if (pid && !isNaN(pid) && pid !== '0') {
              pids.add(pid);
            }
          }
        }
        
        if (pids.size > 0) {
          log(`[killProcessOnPort] Found ${pids.size} process(es) on port ${port}, killing...`);
          const killPromises = Array.from(pids).map((pid) => {
            return new Promise((killResolve) => {
              const killProc = spawn('taskkill', ['/F', '/PID', pid], {
                stdio: ['ignore', 'pipe', 'pipe'],
                shell: true, // Use shell on Windows for better compatibility
              });
              killProc.on('close', (killCode) => {
                if (killCode === 0) {
                  log(`[killProcessOnPort] Killed process ${pid} on port ${port}`);
                  killResolve(true);
                } else {
                  log(`[killProcessOnPort] Failed to kill process ${pid} (exit code ${killCode})`);
                  killResolve(false);
                }
              });
              killProc.on('error', (err) => {
                log(`[killProcessOnPort] Error killing process ${pid}: ${err.message}`);
                killResolve(false);
              });
            });
          });
          Promise.all(killPromises).then(() => resolve(true));
        } else {
          resolve(false);
        }
      } else {
        // macOS/Linux: lsof -ti returns PIDs directly
        const pids = output.trim().split('\n').filter(Boolean);
        if (pids.length > 0) {
          log(`[killProcessOnPort] Found ${pids.length} process(es) on port ${port}, killing...`);
          const killPromises = pids.map((pid) => {
            return new Promise((killResolve) => {
              const killProc = spawn('kill', ['-9', pid], {
                stdio: ['ignore', 'pipe', 'pipe'],
              });
              killProc.on('close', () => {
                log(`[killProcessOnPort] Killed process ${pid} on port ${port}`);
                killResolve(true);
              });
              killProc.on('error', () => killResolve(false));
            });
          });
          Promise.all(killPromises).then(() => resolve(true));
        } else {
          resolve(false);
        }
      }
    });

    proc.on('error', (err) => {
      log(`[killProcessOnPort] Error checking port ${port}: ${err.message}`);
      resolve(false);
    });
  });
}

async function ensurePortsFree() {
  log('[ensurePortsFree] Checking and freeing ports...');
  await Promise.all([
    killProcessOnPort(BACKEND_PORT),
    killProcessOnPort(FRONTEND_PORT),
  ]);
  // Give processes a moment to fully terminate
  await new Promise((resolve) => setTimeout(resolve, 500));
  log('[ensurePortsFree] Ports should be free now');
}

function startBackend() {
  const pythonCmd = resolvePythonPath();
  const args = ['-m', 'uvicorn', 'main:app', '--host', HOST, '--port', String(BACKEND_PORT)];

  log(`[startBackend] Python command: ${pythonCmd}`);
  log(`[startBackend] Backend directory: ${backendDir}`);
  log(`[startBackend] Backend directory exists: ${fs.existsSync(backendDir)}`);
  log(`[startBackend] Bundled runtime directory: ${bundledRuntimeDir}`);
  log(`[startBackend] Bundled runtime exists: ${fs.existsSync(bundledRuntimeDir)}`);
  log(`[startBackend] Python binary exists: ${fs.existsSync(pythonCmd)}`);
  log(`[startBackend] App is packaged: ${app.isPackaged}`);
  log(`[startBackend] Resources path: ${process.resourcesPath}`);

  const pathEnv = fs.existsSync(bundledRuntimeDir)
    ? `${bundledRuntimeDir}${path.delimiter}${DEFAULT_PATH}`
    : DEFAULT_PATH;

  log(`[startBackend] PATH: ${pathEnv}`);
  log(`[startBackend] Starting backend with: ${pythonCmd} ${args.join(' ')}`);

  const proc = spawn(pythonCmd, args, {
    cwd: backendDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      PATH: pathEnv,
    },
  });

  proc.stdout.on('data', (data) => log(`[backend stdout] ${data.toString().trim()}`));
  proc.stderr.on('data', (data) => log(`[backend stderr] ${data.toString().trim()}`));

  proc.on('exit', (code, signal) => {
    log(`[backend] exited with code ${code ?? 'unknown'}, signal ${signal ?? 'none'}`);
  });

  proc.on('error', (err) => {
    log(`[backend] failed to start: ${err.message}`);
    log(`[backend] error stack: ${err.stack}`);
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
  log(`[createWindow] Backend process alive: ${backendProcess && !backendProcess.killed}`);
  log(`[createWindow] Backend process PID: ${backendProcess?.pid || 'none'}`);

  try {
    await waitForServer(BACKEND_PORT, 'Backend');
  } catch (err) {
    log(`[createWindow] Backend failed to start: ${err.message}`);
    log(`[createWindow] Backend process state - killed: ${backendProcess?.killed}, exitCode: ${backendProcess?.exitCode}, signalCode: ${backendProcess?.signalCode}`);

    const errorMsg = `Backend failed to start on port ${BACKEND_PORT}.\n\nCheck log at:\n${logFile}\n\nError: ${err.message}`;
    dialog.showErrorBox('Backend Startup Error', errorMsg);
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

app.whenReady().then(async () => {
  log('[lifecycle] app ready');
  log(`[lifecycle] Platform: ${process.platform}`);
  log(`[lifecycle] Electron version: ${process.versions.electron}`);
  log(`[lifecycle] Node version: ${process.versions.node}`);
  log(`[lifecycle] App path: ${app.getAppPath()}`);
  log(`[lifecycle] User data path: ${app.getPath('userData')}`);
  log(`[lifecycle] Log file: ${logFile}`);

  await ensurePortsFree();

  log('[lifecycle] Starting backend...');
  backendProcess = startBackend();

  log('[lifecycle] Starting frontend...');
  ({ proc: frontendProcess } = startFrontend());

  // Load window immediately; Next.js will come up shortly after on the same port
  log('[lifecycle] Creating window...');
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
