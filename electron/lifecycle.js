const net = require('net');
const { BrowserWindow, dialog } = require('electron');

function checkPortInUse(port, host) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ port, host }, () => {
      socket.end();
      resolve(true);
    });

    socket.on('error', () => {
      socket.destroy();
      resolve(false);
    });
  });
}

async function ensurePortsAvailable({ host, ports, log }) {
  const inUse = [];

  for (const port of ports) {
    const used = await checkPortInUse(port, host);
    if (used) inUse.push(port);
  }

  if (inUse.length > 0) {
    const message = `Ports already in use: ${inUse.join(', ')}`;
    log(`[lifecycle] ${message}`);
    throw new Error(message);
  }
}

function waitForServer({ host, port, label, timeoutMs = 60000, log }) {
  const start = Date.now();
  log(`[waitForServer] waiting for ${label} on ${host}:${port}`);

  return new Promise((resolve, reject) => {
    const attempt = () => {
      const socket = net.createConnection({ port, host }, () => {
        socket.end();
        log(`[waitForServer] ${label} is up on ${host}:${port}`);
        resolve();
      });

      socket.on('error', () => {
        socket.destroy();
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`${label} did not start on port ${port}`));
        } else {
          setTimeout(attempt, 500);
        }
      });
    };

    attempt();
  });
}

async function createWindow({ host, frontendPort, backendPort, log, logFile }) {
  await waitForServer({ host, port: backendPort, label: 'Backend', log });
  await waitForServer({ host, port: frontendPort, label: 'Frontend', log });

  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      contextIsolation: true,
    },
  });

  try {
    await win.loadURL(`http://${host}:${frontendPort}`);
  } catch (err) {
    log(`[lifecycle] failed to load frontend URL: ${err.message}`);
    dialog.showErrorBox('Failed to load UI', `${err.message}\n\nSee log at ${logFile}`);
    throw err;
  }

  return win;
}

module.exports = {
  ensurePortsAvailable,
  createWindow,
};
