"""
Configuration constants and settings.

This module centralizes all configuration values used throughout the application.
Values can be overridden via environment variables for deployment flexibility.
"""

import os
from pathlib import Path

# File upload settings
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))  # Directory where uploaded images are stored
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - maximum size for uploaded image files
MAX_COLLECTION_SIZE = 1000  # Maximum number of images that can be in a single collection

# Database settings
DB_PATH = os.getenv("DB_PATH", "mussel_counter.db")  # SQLite database file path
SCHEMA_PATH = Path(__file__).parent / "schema.sql"  # Path to SQL schema file

# CORS (Cross-Origin Resource Sharing) settings
# These URLs are allowed to make requests to the API (frontend locations)
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

# Model inference settings
DEFAULT_THRESHOLD = 0.5  # Default confidence threshold for mussel detection (0.0 to 1.0)

# Ensure upload directory exists on startup
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
