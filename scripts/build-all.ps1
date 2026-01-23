$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=== Building MusselCounter ===" -ForegroundColor Green
Write-Host "Project root: $ProjectRoot"

# 1. Build frontend
Write-Host "`n=== Building Frontend ===" -ForegroundColor Cyan
Set-Location "$ProjectRoot\frontend"
npm install
npm run build

# Flatten the Next.js standalone output (Next.js bakes in absolute paths)
Write-Host "`nFlattening Next.js standalone output..." -ForegroundColor Cyan
$StandaloneDir = Join-Path $ProjectRoot "frontend\.next\standalone"
$StandaloneFlat = Join-Path $ProjectRoot "frontend\.next\standalone-flat"
$ServerJs = Get-ChildItem -Path $StandaloneDir -Filter "server.js" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "node_modules" } |
    Select-Object -First 1
if ($ServerJs) {
    $ServerDir = Split-Path -Parent $ServerJs.FullName
    Write-Host "Found server.js at: $ServerDir"
    if (Test-Path $StandaloneFlat) {
        Remove-Item -Recurse -Force $StandaloneFlat
    }
    Copy-Item -Recurse -Force $ServerDir $StandaloneFlat
    Write-Host "Flattened standalone output to: $StandaloneFlat"
} else {
    Write-Host "Warning: Could not find server.js in standalone output" -ForegroundColor Yellow
}

# 2. Build backend with PyInstaller
Write-Host "`n=== Building Backend ===" -ForegroundColor Cyan
Set-Location "$ProjectRoot\backend"

# Activate venv
if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
}

# Ensure pyinstaller is installed
pip install pyinstaller

# Clean previous build
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# Build with PyInstaller (retry on transient file locks)
$maxAttempts = 3
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    Write-Host "Running PyInstaller (attempt $attempt/$maxAttempts)..." -ForegroundColor Cyan
    pyinstaller mussel-backend.spec
    if ($LASTEXITCODE -eq 0) {
        break
    }
    if ($attempt -lt $maxAttempts) {
        Write-Host "PyInstaller failed, retrying..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
        Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
    } else {
        throw "PyInstaller failed after $maxAttempts attempts. Check output above for details."
    }
}

Write-Host "`n=== Backend binary created ===" -ForegroundColor Green

# 3. Package Electron app
Write-Host "`n=== Packaging Electron App ===" -ForegroundColor Cyan
Set-Location "$ProjectRoot\electron"
npm install
node scripts/generate-icons.js
$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
# Build Windows installer
npx electron-builder --win
if ($LASTEXITCODE -ne 0) {
    throw "electron-builder failed with exit code $LASTEXITCODE"
}

Write-Host "`n=== Build Complete ===" -ForegroundColor Green
Write-Host "Output: $ProjectRoot\dist\"
