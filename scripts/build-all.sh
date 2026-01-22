#!/bin/bash
# Unified build script for MusselCounter
# Builds frontend, backend (PyInstaller), and packages Electron app
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Building MusselCounter ==="
echo "Project root: $PROJECT_ROOT"

# 1. Build frontend
echo ""
echo "=== Building Frontend ==="
cd "$PROJECT_ROOT/frontend"
npm install
npm run build

# Flatten the Next.js standalone output (Next.js bakes in absolute paths)
# Find the server.js location and move contents to a stable path
echo "Flattening Next.js standalone output..."
STANDALONE_DIR="$PROJECT_ROOT/frontend/.next/standalone"
STANDALONE_FLAT="$PROJECT_ROOT/frontend/.next/standalone-flat"

# Find where server.js actually is (Next.js nests it under the absolute path)
SERVER_JS=$(find "$STANDALONE_DIR" -name "server.js" -not -path "*/node_modules/*" 2>/dev/null | head -1)
if [ -n "$SERVER_JS" ]; then
    SERVER_DIR=$(dirname "$SERVER_JS")
    echo "Found server.js at: $SERVER_DIR"
    
    # Create flattened output
    rm -rf "$STANDALONE_FLAT"
    cp -R "$SERVER_DIR" "$STANDALONE_FLAT"
    
    echo "Flattened standalone output to: $STANDALONE_FLAT"
else
    echo "Warning: Could not find server.js in standalone output"
fi

# 2. Build backend with PyInstaller
echo ""
echo "=== Building Backend ==="
cd "$PROJECT_ROOT/backend"

# Activate venv if it exists, otherwise create it
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Ensure pyinstaller is installed
pip install pyinstaller

# Clean previous build
rm -rf build dist

# Build with PyInstaller
echo "Running PyInstaller..."
pyinstaller mussel-backend.spec

# Ensure executable permission
chmod +x "$PROJECT_ROOT/backend/dist/mussel-backend"

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
