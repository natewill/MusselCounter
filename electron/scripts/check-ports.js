const net = require('net');

const HOST = process.env.HOST || '127.0.0.1';
const FRONTEND_PORT = Number(process.env.FRONTEND_PORT) || 3000;
const BACKEND_PORT = Number(process.env.BACKEND_PORT) || 8000;

const ports = [
  { label: 'Backend', port: BACKEND_PORT },
  { label: 'Frontend', port: FRONTEND_PORT },
];

function checkPort({ port, label }) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    const onResult = (inUse) => {
      socket.destroy();
      resolve({ port, label, inUse });
    };

    socket.setTimeout(2000);
    socket.once('error', (err) => {
      if (err.code === 'ECONNREFUSED' || err.code === 'EHOSTUNREACH' || err.code === 'ETIMEDOUT') {
        onResult(false);
      } else {
        onResult(false);
      }
    });
    socket.once('timeout', () => onResult(false));

    socket.connect(port, HOST, () => onResult(true));
  });
}

async function main() {
  const results = await Promise.all(ports.map(checkPort));
  let blocked = false;

  for (const { label, port, inUse } of results) {
    if (inUse) {
      console.log(`✖ ${label} port ${port} is already in use`);
      blocked = true;
    } else {
      console.log(`✔ ${label} port ${port} is free`);
    }
  }

  if (blocked) {
    console.log('\nClose the processes using the listed ports (3000/8000 by default) or set FRONTEND_PORT/BACKEND_PORT before launching.');
    process.exit(1);
  } else {
    console.log('\nPorts look good.');
  }
}

main().catch((err) => {
  console.error('Port check failed:', err);
  process.exit(1);
});
