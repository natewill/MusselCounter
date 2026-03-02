const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { dialog } = require('electron');

function resolveBackendBinary(app) {
  const binaryName = process.platform === 'win32' ? 'mussel-backend.exe' : 'mussel-backend';

  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend', binaryName);
  }

  return path.join(__dirname, '..', 'backend', 'dist', binaryName);
}

function startBackend({ app, host, backendPort, log }) {
  const backendBinary = resolveBackendBinary(app);
  log(`[backend] binary: ${backendBinary}`);

  if (!fs.existsSync(backendBinary)) {
    const message = `Backend binary not found:\n${backendBinary}`;
    log(`[backend] ${message}`);
    dialog.showErrorBox('Backend Error', message);
    return null;
  }

  const userDataPath = app.getPath('userData');
  const dataDir = path.join(userDataPath, 'data');
  const uploadsDir = path.join(dataDir, 'uploads');
  const modelsDir = path.join(dataDir, 'models');
  const polygonsDir = path.join(dataDir, 'polygons');
  const dbPath = path.join(userDataPath, 'mussel_counter.db');

  [dataDir, uploadsDir, modelsDir, polygonsDir].forEach((dir) => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      log(`[backend] created directory: ${dir}`);
    }
  });

  const proc = spawn(backendBinary, [], {
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      HOST: host,
      BACKEND_PORT: String(backendPort),
      UPLOAD_DIR: uploadsDir,
      MODELS_DIR: modelsDir,
      DB_PATH: dbPath,
      BACKEND_DATA_DIR: dataDir,
      POLYGON_DIR: polygonsDir,
    },
  });

  proc.stdout.on('data', (data) => log(`[backend stdout] ${data.toString().trim()}`));
  proc.stderr.on('data', (data) => log(`[backend stderr] ${data.toString().trim()}`));

  proc.on('exit', (code, signal) => {
    log(`[backend] exited with code ${code ?? 'unknown'}, signal ${signal ?? 'none'}`);
  });

  proc.on('error', (err) => {
    log(`[backend] failed to start: ${err.message}`);
    dialog.showErrorBox(
      'Backend Error',
      `Failed to start backend: ${err.message}\n\nCheck binary at:\n${backendBinary}`
    );
  });

  return proc;
}

module.exports = {
  startBackend,
};
