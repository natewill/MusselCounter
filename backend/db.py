"""
Database connection and initialization utilities.

This module provides:
- Database connection management (context manager for automatic cleanup)
- Database initialization (creates tables from schema.sql)
- Database version tracking (to detect schema changes)
"""

import aiosqlite
from contextlib import asynccontextmanager
from config import DB_PATH, SCHEMA_PATH, RESET_DB_ON_STARTUP, MODELS_DIR
from datetime import datetime, timezone


async def _initialize_models(db: aiosqlite.Connection):
    """
    Initialize database with default models from models/ directory.
    
    Note: Batch size detection is now done on-demand when models are loaded,
    not during initialization. This makes startup faster.
    """
    models_dir = MODELS_DIR
    if not models_dir.exists():
        return
    
    model_files = list(models_dir.glob("*.pt")) + list(models_dir.glob("*.pth"))
    if not model_files:
        return
    
    for model_file in model_files:
        # Infer model type from filename
        filename_lower = model_file.name.lower()
        if "yolo" in filename_lower:
            model_type = "YOLO"
        elif "cnn" in filename_lower or "faster" in filename_lower:
            model_type = "Faster R-CNN"
        else:
            model_type = "YOLO"  # Default to YOLO
        
        # Check if model already exists
        cursor = await db.execute(
            "SELECT model_id FROM model WHERE weights_path = ?",
            (str(model_file),)
        )
        existing = await cursor.fetchone()
        
        if not existing:
            # Add model to database (batch size will be detected on first load)
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                """INSERT INTO model (name, type, weights_path, description, optimal_batch_size, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    model_file.stem,
                    model_type,
                    str(model_file),
                    f"Auto-detected {model_type} model",
                    8,  # Default value (will be detected and cached on first load)
                    now,
                    now
                )
            )
    
    await db.commit()


@asynccontextmanager
async def get_db():
    """
    Context manager for database connections.
    
    Provides a database connection that automatically:
    - Opens connection when entering context
    - Sets row factory to return dict-like rows (access columns by name)
    - Closes connection when exiting context
    
    Usage:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM batch")
            rows = await cursor.fetchall()
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable row factory to return dict-like rows (access by column name)
        # Without this, rows would be tuples accessed by index
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    """
    Initialize the database by creating all tables from schema.sql.
    
    This function:
    1. Deletes existing database if found (development mode - in production use migrations)
    2. Reads schema.sql and executes it to create all tables
    3. Creates db_metadata table for tracking database version
    4. Stores initialization timestamp in metadata
    
    Note: In production, you'd want proper database migrations instead of
    deleting and recreating the database.
    """
    import os

    # Skip re-initialization if database already exists and reset flag is not set
    if os.path.exists(DB_PATH) and not RESET_DB_ON_STARTUP:
        return

    # Delete existing database when reset flag is enabled
    if os.path.exists(DB_PATH) and RESET_DB_ON_STARTUP:
        os.remove(DB_PATH)

    # Read the schema file containing CREATE TABLE statements
    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()

    # Execute the schema to create all tables
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(schema)  # Execute all SQL statements in schema file

        # Create metadata table to store database version/reset timestamp
        # This allows the frontend to detect when database was reset and refresh data
        # IF NOT EXISTS prevents error if table already exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS db_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Check if metadata already exists (for existing databases that weren't reset)
        cursor = await db.execute(
            "SELECT value FROM db_metadata WHERE key = ?", ("db_init_timestamp",)
        )
        existing_metadata = await cursor.fetchone()

        if not existing_metadata:
            # Store database initialization timestamp (new database or existing without metadata)
            # Frontend can check this to detect database resets
            init_timestamp = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("db_init_timestamp", init_timestamp),
            )
            await db.commit()
        
        # Models are now added via the API endpoint, not automatically on startup
        await _initialize_models(db)


async def get_db_version(db: aiosqlite.Connection) -> str | None:
    """Get the database version/timestamp"""
    cursor = await db.execute(
        "SELECT value FROM db_metadata WHERE key = ?", ("db_init_timestamp",)
    )
    row = await cursor.fetchone()
    return row["value"] if row else None
