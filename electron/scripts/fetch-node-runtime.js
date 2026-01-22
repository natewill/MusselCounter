const fs = require('fs');
const path = require('path');
const https = require('https');

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) {
        args[key] = true;
      } else {
        args[key] = next;
        i += 1;
      }
    }
  }
  return args;
}

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const request = https.get(url, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.resume();
        return resolve(downloadFile(res.headers.location, dest));
      }

      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error(`Download failed: ${res.statusCode} ${res.statusMessage}`));
      }

      const file = fs.createWriteStream(dest);
      res.pipe(file);
      file.on('finish', () => {
        file.close(resolve);
      });
      file.on('error', (err) => {
        fs.unlink(dest, () => reject(err));
      });
    });

    request.on('error', reject);
  });
}

async function main() {
  const args = parseArgs(process.argv);
  const platform = args.platform || 'win32';
  const arch = args.arch || 'x64';
  const version = args.version || process.env.NODE_RUNTIME_VERSION || '20.11.1';
  const force = Boolean(args.force || process.env.NODE_RUNTIME_FORCE);

  if (platform !== 'win32') {
    throw new Error(`Unsupported platform: ${platform}`);
  }

  const repoRoot = path.resolve(__dirname, '..', '..');
  const targetDir = path.join(repoRoot, 'node-runtime', platform);
  const targetFile = path.join(targetDir, 'node.exe');

  if (!force && fs.existsSync(targetFile)) {
    console.log(`[fetch-node-runtime] Using existing ${targetFile}`);
    return;
  }

  await fs.promises.mkdir(targetDir, { recursive: true });

  const url = `https://nodejs.org/dist/v${version}/win-${arch}/node.exe`;
  console.log(`[fetch-node-runtime] Downloading ${url}`);
  await downloadFile(url, targetFile);
  console.log(`[fetch-node-runtime] Saved to ${targetFile}`);
}

main().catch((err) => {
  console.error(`[fetch-node-runtime] ${err.message}`);
  process.exit(1);
});
