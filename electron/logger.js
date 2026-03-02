const fs = require('fs');
const path = require('path');

function createLogger(app) {
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

  return { log, logFile };
}

module.exports = {
  createLogger,
};
