const fs = require('fs');
const path = require('path');
const iconGen = require('icon-gen');

const repoRoot = path.resolve(__dirname, '..', '..');
const frontendDir = path.join(repoRoot, 'frontend');
const sourceSvg = path.join(frontendDir, 'app', 'icon.svg');
const outputDir = path.join(frontendDir, 'public');

async function ensureSourceExists() {
  if (!fs.existsSync(sourceSvg)) {
    throw new Error(`Source icon not found at ${sourceSvg}`);
  }
}

async function generateIcons() {
  await ensureSourceExists();
  await fs.promises.mkdir(outputDir, { recursive: true });

  await iconGen(sourceSvg, outputDir, {
    report: false,
    modes: ['icns', 'ico', 'favicon'],
    icns: { sizes: [512, 1024] },
    ico: { sizes: [16, 24, 32, 48, 64, 128, 256] },
    favicon: {
      pngSizes: [32, 64, 128, 256, 512],
      icoSizes: [16, 32, 48, 64],
    },
  });

  // Use the 512x512 PNG as the canonical app icon for Linux/others
  const png512 = fs.existsSync(path.join(outputDir, 'favicon-512x512.png'))
    ? path.join(outputDir, 'favicon-512x512.png')
    : path.join(outputDir, 'favicon-512.png');
  const appPng = path.join(outputDir, 'icon.png');
  if (fs.existsSync(png512)) {
    await fs.promises.copyFile(png512, appPng);
  }

  // Normalize names expected by electron-builder
  const iconIcns = path.join(outputDir, 'icon.icns');
  const fallbackIcns = path.join(outputDir, 'app.icns');
  if (!fs.existsSync(iconIcns) && fs.existsSync(fallbackIcns)) {
    await fs.promises.rename(fallbackIcns, iconIcns);
  }

  const iconIco = path.join(outputDir, 'icon.ico');
  const fallbackIco = path.join(outputDir, 'app.ico');
  if (!fs.existsSync(iconIco) && fs.existsSync(fallbackIco)) {
    await fs.promises.rename(fallbackIco, iconIco);
  }

  console.log(`Generated icons in ${outputDir}`);
  console.log('- icon.icns (macOS), icon.ico (Windows), icon.png (Linux/others)');
}

generateIcons().catch((err) => {
  console.error('Icon generation failed:', err);
  process.exit(1);
});
