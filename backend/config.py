"""
Configuration constants and settings.

This module centralizes all configuration values used throughout the application.
Values can be overridden via environment variables for deployment flexibility.
"""

import os
from pathlib import Path

# Base data directory (writable). Defaults to local ./data but can be overridden (e.g., Electron userData)
DATA_DIR = Path(os.getenv("BACKEND_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# File upload settings
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", DATA_DIR / "uploads"))  # Directory where uploaded images are stored
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - maximum size for uploaded image files
MAX_MODEL_SIZE = 1024 * 1024 * 1024  # 1GB - maximum size for uploaded model files
MAX_COLLECTION_SIZE = 1000  # Maximum number of images that can be in a single collection

# Model settings
_DEFAULT_MODELS_DIR = DATA_DIR / "models"
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(_DEFAULT_MODELS_DIR)))

# Database settings
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "mussel_counter.db"))  # SQLite database file path
SCHEMA_PATH = Path(__file__).parent / "schema.sql"  # Path to SQL schema file
RESET_DB_ON_STARTUP = os.getenv("RESET_DB_ON_STARTUP", "false").lower() in {"1", "true", "yes"}

# Polygon storage
POLYGON_DIR = Path(os.getenv("POLYGON_DIR", DATA_DIR / "polygons"))

# CORS (Cross-Origin Resource Sharing) settings
# For a solo app we default to allowing any origin. To restrict, set FRONTEND_URL.
FRONTEND_URL = os.getenv("FRONTEND_URL")
if FRONTEND_URL:
    CORS_ORIGINS = [
        FRONTEND_URL,
        FRONTEND_URL.replace("localhost", "127.0.0.1") if "localhost" in FRONTEND_URL else None,
    ]
    CORS_ORIGINS = [origin for origin in CORS_ORIGINS if origin]
else:
    CORS_ORIGINS = ["*"]

# Model inference settings
DEFAULT_THRESHOLD = 0.5  # Default confidence threshold for mussel detection (0.0 to 1.0)

# Ensure upload directory exists on startup
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Ensure model directory exists so startup detection doesn't fail
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Ensure polygon directory exists
POLYGON_DIR.mkdir(parents=True, exist_ok=True)
