const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { dialog } = require('electron');
const { DEFAULT_PATH } = require('./config');

function resolveNodePath(log) {
  const bundledNode = process.platform === 'win32'
    ? path.join(process.resourcesPath, 'node', 'node.exe')
    : path.join(process.resourcesPath, 'node', 'bin', 'node');

  const candidates = [
    process.env.NODE_BINARY,
    process.env.NEXT_NODE_BINARY,
    bundledNode,
    process.platform === 'win32' ? 'node.exe' : 'node',
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (candidate === 'node' || candidate === 'node.exe') {
      log(`[frontend] using Node from PATH: ${candidate}`);
      return candidate;
    }

    if (fs.existsSync(candidate)) {
      log(`[frontend] using Node binary: ${candidate}`);
      return candidate;
    }
  }

  log('[frontend] no Node.js runtime found');
  return null;
}

function resolveStandaloneServer(app) {
  const baseDir = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..');
  const frontendDir = path.join(baseDir, 'frontend');

  const candidates = [
    process.env.FRONTEND_SERVER_JS,
    path.join(frontendDir, 'server.js'),
    path.join(frontendDir, '.next', 'standalone', 'server.js'),
    path.join(frontendDir, '.next', 'standalone-flat', 'server.js'),
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return { frontendDir, serverJs: candidate };
    }
  }

  return { frontendDir, serverJs: candidates[1] };
}

function startFrontend({ app, host, frontendPort, log }) {
  const { frontendDir, serverJs } = resolveStandaloneServer(app);

  if (!fs.existsSync(serverJs)) {
    const message = `Frontend standalone server not found:\n${serverJs}\n\nBuild frontend standalone output first.`;
    log(`[frontend] ${message}`);
    dialog.showErrorBox('Frontend Error', message);
    return null;
  }

  const nodeCmd = resolveNodePath(log);
  if (!nodeCmd) {
    dialog.showErrorBox(
      'Node.js not found',
      'Could not find a Node.js runtime to start the frontend. Set NODE_BINARY/NEXT_NODE_BINARY or bundle node with the app.'
    );
    return null;
  }

  const env = {
    ...process.env,
    PATH: DEFAULT_PATH,
    NODE_ENV: 'production',
    HOSTNAME: host,
    PORT: String(frontendPort),
  };
  delete env.ELECTRON_RUN_AS_NODE;

  const proc = spawn(nodeCmd, [serverJs], {
    cwd: path.dirname(serverJs),
    stdio: ['ignore', 'pipe', 'pipe'],
    env,
  });

  proc.stdout.on('data', (data) => log(`[frontend stdout] ${data.toString().trim()}`));
  proc.stderr.on('data', (data) => log(`[frontend stderr] ${data.toString().trim()}`));

  proc.on('exit', (code) => {
    log(`[frontend] exited with code ${code ?? 'unknown'}`);
    if (code && code !== 0) {
      dialog.showErrorBox('Frontend exited', `Frontend server exited with code ${code}.`);
    }
  });

  proc.on('error', (err) => {
    log(`[frontend] failed to start: ${err.message}`);
    dialog.showErrorBox('Frontend start error', err.message);
  });

  return proc;
}

module.exports = {
  startFrontend,
};
