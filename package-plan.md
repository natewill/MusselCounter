# PyInstaller Migration Plan

**Goal:** Replace the bundled Python runtime with a PyInstaller-compiled backend executable for simpler, more reliable packaging.

**Current State:** Electron app bundles an entire `python-runtime/` directory (~500MB+) and spawns `python -m uvicorn main:app`. This causes version compatibility issues and complex packaging.

**Target State:** Backend compiled to a single executable (`mussel-backend` or `mussel-backend.exe`) that Electron spawns directly.

---

## Phase 1: PyInstaller Setup

### 1.1 Install PyInstaller in backend

```bash
cd backend
source venv/bin/activate
pip install pyinstaller
pip freeze > requirements.txt  # Update if needed
```

### 1.2 Create PyInstaller spec file

Create `backend/mussel-backend.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all hidden imports for ML libraries
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'uvicorn',
    'fastapi',
    'starlette',
    'pydantic',
    'aiosqlite',
    'aiofiles',
    'torch',
    'torchvision',
    'ultralytics',
    'PIL',
    'cv2',
    'numpy',
]

# Add ultralytics submodules (YOLO)
hiddenimports += collect_submodules('ultralytics')

# Collect data files needed at runtime
datas = []
datas += collect_data_files('ultralytics')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mussel-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep True for logging; backend runs headless
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### 1.3 Create entry point wrapper

Create `backend/main_entry.py` (PyInstaller entry point that starts uvicorn programmatically):

```python
"""
Entry point for PyInstaller build.
Starts uvicorn programmatically instead of via CLI.
"""
import os
import sys
import uvicorn

def main():
    # Get configuration from environment or use defaults
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('BACKEND_PORT', '8000'))

    # Import the FastAPI app
    from main import app

    # Run uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )

if __name__ == "__main__":
    main()
```

Update the spec file to use `main_entry.py` instead of `main.py`:
```python
a = Analysis(
    ['main_entry.py'],  # Changed from main.py
    ...
)
```

### 1.4 Test PyInstaller build locally

```bash
cd backend
source venv/bin/activate

# Build the executable
pyinstaller mussel-backend.spec

# Test it
./dist/mussel-backend
# Should start server on http://127.0.0.1:8000
```

**Expected output location:** `backend/dist/mussel-backend` (or `.exe` on Windows)

---

## Phase 2: Update Electron Configuration

### 2.1 Modify `electron/main.js`

Replace the Python spawning logic with binary spawning.

**Find and replace the `startBackend()` function:**

```javascript
function startBackend() {
  // Determine the backend binary path
  const binaryName = process.platform === 'win32' ? 'mussel-backend.exe' : 'mussel-backend';

  let backendBinary;
  if (app.isPackaged) {
    // In packaged app, binary is in resources
    backendBinary = path.join(process.resourcesPath, 'backend', binaryName);
  } else {
    // In development, use the dist folder from PyInstaller
    backendBinary = path.join(__dirname, '..', 'backend', 'dist', binaryName);
  }

  log(`[startBackend] Backend binary: ${backendBinary}`);
  log(`[startBackend] Binary exists: ${fs.existsSync(backendBinary)}`);

  // Set up writable data directories in userData
  const userDataPath = app.getPath('userData');
  const dataDir = path.join(userDataPath, 'data');
  const uploadsDir = path.join(dataDir, 'uploads');
  const modelsDir = path.join(dataDir, 'models');
  const polygonsDir = path.join(dataDir, 'polygons');
  const dbPath = path.join(userDataPath, 'mussel_counter.db');

  // Create directories if they don't exist
  [dataDir, uploadsDir, modelsDir, polygonsDir].forEach((dir) => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      log(`[startBackend] Created directory: ${dir}`);
    }
  });

  log(`[startBackend] Starting backend binary...`);

  const proc = spawn(backendBinary, [], {
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      HOST: HOST,
      BACKEND_PORT: String(BACKEND_PORT),
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
      `Failed to start backend: ${err.message}\n\nCheck that the backend binary exists at:\n${backendBinary}`
    );
  });

  return proc;
}
```

**Remove these functions (no longer needed):**
- `resolvePythonPath()`
- Any references to `bundledPython`, `bundledRuntimeDir`, `PYTHON_PATH`

### 2.2 Update `electron/package.json` build config

Replace the backend extraResources section:

```json
{
  "build": {
    "extraResources": [
      {
        "from": "../backend/dist/mussel-backend${os === 'win32' ? '.exe' : ''}",
        "to": "backend/mussel-backend${os === 'win32' ? '.exe' : ''}"
      },
      {
        "from": "../frontend/.next/standalone",
        "to": "frontend",
        "filter": ["**/*"]
      },
      {
        "from": "../frontend/.next/static",
        "to": "frontend/.next/static",
        "filter": ["**/*"]
      },
      {
        "from": "../frontend/public",
        "to": "frontend/public",
        "filter": ["**/*"]
      },
      {
        "from": "../README.md",
        "to": "README.md"
      }
    ]
  }
}
```

**Note:** electron-builder doesn't support `${os}` syntax. Use platform-specific overrides instead:

```json
{
  "build": {
    "extraResources": [
      {
        "from": "../frontend/.next/standalone",
        "to": "frontend",
        "filter": ["**/*"]
      },
      {
        "from": "../frontend/.next/static",
        "to": "frontend/.next/static",
        "filter": ["**/*"]
      },
      {
        "from": "../frontend/public",
        "to": "frontend/public",
        "filter": ["**/*"]
      },
      {
        "from": "../README.md",
        "to": "README.md"
      }
    ],
    "mac": {
      "extraResources": [
        {
          "from": "../backend/dist/mussel-backend",
          "to": "backend/mussel-backend"
        }
      ]
    },
    "win": {
      "extraResources": [
        {
          "from": "../backend/dist/mussel-backend.exe",
          "to": "backend/mussel-backend.exe"
        }
      ]
    },
    "linux": {
      "extraResources": [
        {
          "from": "../backend/dist/mussel-backend",
          "to": "backend/mussel-backend"
        }
      ]
    }
  }
}
```

---

## Phase 3: Build Scripts

### 3.1 Create unified build script

Create `scripts/build-all.sh` at project root:

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Building MusselCounter ==="

# 1. Build frontend
echo ""
echo "=== Building Frontend ==="
cd "$PROJECT_ROOT/frontend"
npm install
npm run build

# 2. Build backend with PyInstaller
echo ""
echo "=== Building Backend ==="
cd "$PROJECT_ROOT/backend"

# Activate venv if it exists, otherwise create it
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install pyinstaller
fi

# Clean previous build
rm -rf build dist

# Build with PyInstaller
pyinstaller mussel-backend.spec

echo ""
echo "=== Backend binary created at: $PROJECT_ROOT/backend/dist/mussel-backend ==="

# 3. Package Electron app
echo ""
echo "=== Packaging Electron App ==="
cd "$PROJECT_ROOT/electron"
npm install
npm run pack

echo ""
echo "=== Build Complete ==="
echo "Output: $PROJECT_ROOT/dist/"
```

### 3.2 Create Windows build script

Create `scripts/build-all.ps1`:

```powershell
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=== Building MusselCounter ===" -ForegroundColor Green

# 1. Build frontend
Write-Host "`n=== Building Frontend ===" -ForegroundColor Cyan
Set-Location "$ProjectRoot\frontend"
npm install
npm run build

# 2. Build backend with PyInstaller
Write-Host "`n=== Building Backend ===" -ForegroundColor Cyan
Set-Location "$ProjectRoot\backend"

# Activate venv
if (Test-Path "venv\Scripts\activate.ps1") {
    .\venv\Scripts\Activate.ps1
} else {
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    pip install pyinstaller
}

# Clean previous build
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# Build with PyInstaller
pyinstaller mussel-backend.spec

Write-Host "`n=== Backend binary created ===" -ForegroundColor Green

# 3. Package Electron app
Write-Host "`n=== Packaging Electron App ===" -ForegroundColor Cyan
Set-Location "$ProjectRoot\electron"
npm install
npm run pack

Write-Host "`n=== Build Complete ===" -ForegroundColor Green
Write-Host "Output: $ProjectRoot\dist\"
```

---

## Phase 4: Cleanup

### 4.1 Remove old Python runtime code

After confirming the new approach works:

1. **Delete** `electron/node-runtime/` directory (if exists)
2. **Delete** `backend/python-runtime/` directory (if exists)
3. **Remove** from `electron/main.js`:
   - `resolvePythonPath()` function
   - `bundledPython`, `bundledRuntimeDir` variables
   - Any `PYTHON_PATH` references
4. **Remove** from `electron/package.json`:
   - The old `extraResources` entries for `python-runtime`
   - Any Python-related filters

### 4.2 Update .gitignore

Add to `.gitignore`:
```
# PyInstaller
backend/build/
backend/dist/
backend/*.spec.bak
```

---

## Phase 5: Testing Checklist

### 5.1 Local development testing
- [ ] `cd backend && pyinstaller mussel-backend.spec` completes without errors
- [ ] `./backend/dist/mussel-backend` starts and responds to API requests
- [ ] Frontend can communicate with backend binary
- [ ] All API endpoints work (collections, models, runs, images)
- [ ] ML inference works (model loading, detection)

### 5.2 Packaged app testing
- [ ] `npm run pack` completes without errors
- [ ] App opens without "backend not found" errors
- [ ] Backend starts successfully (check logs)
- [ ] Frontend loads and connects to backend
- [ ] Full workflow: upload images → run model → view results

### 5.3 Platform-specific testing
- [ ] macOS (Apple Silicon)
- [ ] macOS (Intel) - if supporting
- [ ] Windows 10/11
- [ ] Linux (Ubuntu/Debian)

---

## Troubleshooting

### Common PyInstaller Issues

**Issue:** `ModuleNotFoundError` at runtime
**Solution:** Add missing module to `hiddenimports` in spec file

**Issue:** Missing data files (model configs, etc.)
**Solution:** Add to `datas` in spec file:
```python
datas += [('path/to/file', 'destination/folder')]
```

**Issue:** Binary is huge (>1GB)
**Solution:**
- Add unused packages to `excludes`
- Use `--exclude-module` for test frameworks
- Consider using `--onedir` instead of `--onefile` for faster startup

**Issue:** Antivirus flags the executable
**Solution:** This is common with PyInstaller. Sign the executable or whitelist it.

### Electron Issues

**Issue:** Backend binary not found
**Solution:** Check `extraResources` paths match actual build output

**Issue:** Binary doesn't have execute permission (macOS/Linux)
**Solution:** Add to build script:
```bash
chmod +x "$PROJECT_ROOT/backend/dist/mussel-backend"
```

---

## Expected Results

After completing this migration:

| Metric | Before (Python Runtime) | After (PyInstaller) |
|--------|------------------------|---------------------|
| Backend size | ~500MB+ | ~200-300MB |
| Packaging complexity | High | Low |
| Python version issues | Common | None |
| Cross-platform builds | Complex | Simple (per-platform) |
| Startup reliability | Fragile | Robust |

---

## File Changes Summary

| File | Action |
|------|--------|
| `backend/mussel-backend.spec` | Create |
| `backend/main_entry.py` | Create |
| `backend/requirements.txt` | Add `pyinstaller` |
| `electron/main.js` | Modify `startBackend()` |
| `electron/package.json` | Update `extraResources` |
| `scripts/build-all.sh` | Create |
| `scripts/build-all.ps1` | Create |
| `backend/python-runtime/` | Delete (after migration) |
| `.gitignore` | Update |
