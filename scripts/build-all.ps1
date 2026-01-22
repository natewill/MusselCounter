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

# Build with PyInstaller
Write-Host "Running PyInstaller..." -ForegroundColor Cyan
pyinstaller mussel-backend.spec

Write-Host "`n=== Backend binary created ===" -ForegroundColor Green

# 3. Package Electron app
Write-Host "`n=== Packaging Electron App ===" -ForegroundColor Cyan
Set-Location "$ProjectRoot\electron"
npm install
npm run pack

Write-Host "`n=== Build Complete ===" -ForegroundColor Green
Write-Host "Output: $ProjectRoot\dist\"
