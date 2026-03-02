const HOST = '127.0.0.1';
const FRONTEND_PORT = Number(process.env.FRONTEND_PORT) || 3000;
const BACKEND_PORT = Number(process.env.BACKEND_PORT) || 8000;
const DEFAULT_PATH =
  process.env.PATH ||
  '/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin';

module.exports = {
  HOST,
  FRONTEND_PORT,
  BACKEND_PORT,
  DEFAULT_PATH,
};
